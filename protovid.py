"""PROTOVID // Windows-focused desktop UI (Tk + OpenCV + FFmpeg)."""
from __future__ import annotations
import copy
import json
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image,ImageTk
from protovid_core import Mask, apply_masks, clamp_box, export_video, split_segment, track_range

INK='#080B0D'; PANEL='#13191C'; PANEL2='#1B2326'; YELLOW='#E6C13C'; WHITE='#E8E9E6'; MUTED='#9BA7A6'; GRAY='#30393D'

class ProToVid:
    def __init__(self,root):
        self.root=root;root.title('PROTOVID  |  FIELD VIDEO EDITOR  |  WINDOWS')
        root.geometry('1460x900');root.minsize(1080,700);root.configure(bg=INK)
        self.path=None;self.cap=None;self.frames=0;self.fps=25.0;self.width=0;self.height=0
        self.pos=0;self.masks=[];self.selected=-1;self.segments=[]
        self.playing=False;self.play_mark=0;self.task=None;self.events=queue.Queue()
        self.photo=None;self.canvas_geometry=(1,0,0);self.mouse=None;self.is_seek=False
        self._suppress=False;self.build();self.root.after(60,self.poll_events)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.bind('<Control-s>',lambda e:self.save_project())
        self.root.bind('<Control-o>',lambda e:self.open_video())
        self.root.bind('<space>',lambda e:self.toggle_play() if not isinstance(e.widget,tk.Entry) else None)

    def makebutton(self,parent,label,action,accent=False):
        return tk.Button(parent,text=label,command=action,bg=YELLOW if accent else '#D2D7D5',
                         fg='#121719',activebackground='#F4D975',activeforeground='#0E1213',
                         font=('Segoe UI',9,'bold'),padx=11,pady=8,relief='flat',cursor='hand2')

    def label(self,parent,text,color=MUTED, size=10,bold=False):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                        font=('Segoe UI',size,'bold' if bold else 'normal'),anchor='w')

    def frame(self,parent,bg=PANEL):return tk.Frame(parent,bg=bg)

    def heading(self,parent,text):
        x=self.label(parent,text,YELLOW,10,True);x.pack(fill='x',padx=12,pady=(12,7));return x

    def build(self):
        head=self.frame(self.root,INK);head.pack(fill='x',padx=20,pady=(15,8))
        self.label(head,'P R O T O V I D',YELLOW,22,True).pack(side='left')
        self.label(head,'   / /   FIELD VIDEO EDITOR     WINDOWS EDITION',MUTED,10,True).pack(side='left')
        self.makebutton(head,'ZAPISZ PROJEKT',self.save_project).pack(side='left',padx=(20,6))
        self.makebutton(head,'OTWÓRZ PROJEKT',self.open_project).pack(side='left')
        self.status_text=tk.StringVar(value='GOTOWY  •  WCZYTAJ FILM')
        tk.Label(head,textvariable=self.status_text,fg=YELLOW,bg=INK,font=('Segoe UI',9,'bold')).pack(side='right')
        stripe=tk.Canvas(self.root,height=13,bg=INK,highlightthickness=0);stripe.pack(fill='x',padx=20,pady=(0,12))
        self.stripe=stripe;stripe.bind('<Configure>',self.draw_stripe)

        body=self.frame(self.root,INK);body.pack(fill='both',expand=True,padx=20,pady=(0,15))
        left=self.frame(body,INK);left.pack(side='left',fill='both',expand=True,padx=(0,13))
        right=self.frame(body,PANEL);right.pack(side='right',fill='y');right.configure(width=345);right.pack_propagate(False)

        self.canvas=tk.Canvas(left,bg='#030506',highlightthickness=1,highlightbackground=GRAY,cursor='crosshair')
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.render())
        self.canvas.bind('<ButtonPress-1>',self.mouse_down)
        self.canvas.bind('<B1-Motion>',self.mouse_move)
        self.canvas.bind('<ButtonRelease-1>',self.mouse_up)

        controls=self.frame(left,INK);controls.pack(fill='x',pady=(10,4))
        for title,act in [('OTWÓRZ FILM',self.open_video),('◀ KLATKA',lambda:self.seek(self.pos-1)),
                          ('ODTWARZAJ / PAUZA',self.toggle_play),('KLATKA ▶',lambda:self.seek(self.pos+1)),
                          ('KLATKA KLUCZOWA',self.add_key)]:
            self.makebutton(controls,title,act, title=='OTWÓRZ FILM').pack(side='left',padx=(0,5))
        timeline=self.frame(left,INK);timeline.pack(fill='x',pady=(1,4))
        self.timeline=tk.Scale(timeline,from_=0,to=0,orient='horizontal',bg=INK,fg=WHITE,
                               troughcolor=GRAY,highlightthickness=0,bd=0,showvalue=False,
                               activebackground=YELLOW,command=self.slider_move)
        self.timeline.pack(side='left',fill='x',expand=True)
        self.frame_text=tk.StringVar(value='00:00.00  /  00:00.00   |   0 / 0')
        tk.Label(timeline,textvariable=self.frame_text,bg=INK,fg=MUTED,font=('Consolas',10)).pack(side='right',padx=(9,0))

        cutbar=self.frame(left,INK);cutbar.pack(fill='x',pady=(6,7))
        for title,act in [('ROZETNIJ W TYM MIEJSCU',self.cut_here),('▲ PRZESUŃ',lambda:self.move_part(-1)),
                          ('▼ PRZESUŃ',lambda:self.move_part(1)),('USUŃ FRAGMENT',self.delete_part)]:
            self.makebutton(cutbar,title,act, title.startswith('ROZETNIJ')).pack(side='left',padx=(0,6))
        self.partlist=ttk.Treeview(left,columns=('order','start','end','duration'),show='headings',height=5,selectmode='browse')
        for key,label,width in [('order','#',40),('start','POCZĄTEK',110),('end','KONIEC',110),('duration','DŁUGOŚĆ',110)]:
            self.partlist.heading(key,text=label);self.partlist.column(key,width=width,anchor='center')
        self.partlist.pack(fill='x');self.partlist.bind('<<TreeviewSelect>>',self.part_selected)

        self.heading(right,'01 / MASKI I OBSZARY')
        self.masklist=tk.Listbox(right,bg='#101517',fg=WHITE,selectbackground=YELLOW,
                                 selectforeground=INK,highlightthickness=0,relief='flat',height=6,font=('Consolas',10))
        self.masklist.pack(fill='x',padx=12);self.masklist.bind('<<ListboxSelect>>',self.mask_selected)
        maskrow=self.frame(right);maskrow.pack(fill='x',padx=12,pady=(8,5))
        self.makebutton(maskrow,'DODAJ MASKĘ',self.add_center_mask,True).pack(side='left',padx=(0,6))
        self.makebutton(maskrow,'USUŃ',self.delete_mask).pack(side='left')
        self.label(right,'Narysuj prostokąt lub przeciągnij maskę na podglądzie.',MUTED,9).pack(fill='x',padx=12)

        self.heading(right,'02 / PARAMETRY MASKI')
        self.strength=tk.IntVar(value=35)
        self.strength_label=tk.StringVar(value='SIŁA ROZMYCIA    35 / 100')
        self.label(right,'TRYB',MUTED,9,True).pack(fill='x',padx=12)
        self.mode=tk.StringVar(value='Blur')
        modeselect=ttk.Combobox(right,textvariable=self.mode,values=('Blur','Mosaic'),state='readonly')
        modeselect.pack(fill='x',padx=12,pady=(3,9));modeselect.bind('<<ComboboxSelected>>',self.property_changed)
        tk.Label(right,textvariable=self.strength_label,bg=PANEL,fg=WHITE,
                 font=('Segoe UI',9,'bold'),anchor='w').pack(fill='x',padx=12)
        self.blur=tk.Scale(right,from_=1,to=100,orient='horizontal',showvalue=False,variable=self.strength,
                           bg=PANEL,fg=WHITE,troughcolor=GRAY,bd=0,highlightthickness=0,
                           activebackground=YELLOW,command=self.property_changed)
        self.blur.pack(fill='x',padx=12)
        self.enabled=tk.BooleanVar(value=True)
        tk.Checkbutton(right,text='MASKA AKTYWNA',variable=self.enabled,command=self.property_changed,
                       bg=PANEL,fg=WHITE,selectcolor=PANEL2,activebackground=PANEL,
                       activeforeground=YELLOW,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=12,pady=5)
        ranges=self.frame(right);ranges.pack(fill='x',padx=12)
        self.first=tk.StringVar(value='0');self.last=tk.StringVar(value='0')
        for lab,var in [('OD KLATKI',self.first),('DO KLATKI',self.last)]:
            col=self.frame(ranges);col.pack(side='left',fill='x',expand=True,padx=(0,7))
            self.label(col,lab,MUTED,9,True).pack(anchor='w')
            entry=tk.Entry(col,textvariable=var,bg='#E1E6E3',fg=INK,relief='flat',font=('Consolas',11))
            entry.pack(fill='x',pady=(5,2),ipady=4);entry.bind('<Return>',self.range_changed);entry.bind('<FocusOut>',self.range_changed)
        self.heading(right,'03 / ŚLEDZENIE')
        self.makebutton(right,'ŚLEDŹ OD TEJ KLATKI →',lambda:self.track(False),True).pack(fill='x',padx=12,pady=(0,6))
        self.makebutton(right,'← ŚLEDŹ WSTECZ',lambda:self.track(True)).pack(fill='x',padx=12)
        self.label(right,'Korekty: zaznacz maskę, przesuń ją na klatce, zapisz klatkę kluczową.',MUTED,9).pack(fill='x',padx=12,pady=(6,4))
        self.makebutton(right,'ZNAJDŹ TWARZE NA KLATCE',self.detect_faces).pack(fill='x',padx=12)

        self.heading(right,'04 / EKSPORT MP4')
        self.audio=tk.BooleanVar(value=True)
        tk.Checkbutton(right,text='ZACHOWAJ DŹWIĘK (TAKŻE PO CIĘCIACH)',variable=self.audio,
                       bg=PANEL,fg=WHITE,selectcolor=PANEL2,activebackground=PANEL,
                       activeforeground=YELLOW,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=12)
        self.makebutton(right,'EKSPORTUJ H.264 / MP4',self.export,True).pack(fill='x',padx=12,pady=(8,6))
        self.progress=ttk.Progressbar(right,mode='determinate',maximum=100)
        self.progress.pack(fill='x',padx=12,pady=(0,10))
        self.label(right,'PROTOVID  •  OFFLINE  •  LOCAL PROCESSING',MUTED,8,True).pack(side='bottom',padx=12,pady=15)
        self.setup_style()

    def setup_style(self):
        s=ttk.Style(self.root);s.theme_use('clam')
        s.configure('Treeview',background='#111719',foreground=WHITE,fieldbackground='#111719',borderwidth=0,rowheight=24)
        s.map('Treeview',background=[('selected',YELLOW)],foreground=[('selected',INK)])
        s.configure('Treeview.Heading',background=GRAY,foreground=WHITE,font=('Segoe UI',9,'bold'))
        s.configure('TCombobox',fieldbackground='#DEE4E2',background='#DEE4E2',foreground=INK)
        s.configure('TProgressbar',background=YELLOW,troughcolor=GRAY)

    def draw_stripe(self,event=None):
        c=self.stripe;c.delete('all');w=c.winfo_width();h=c.winfo_height()
        c.create_rectangle(0,2,w,h-2,fill='#B99521',outline='')
        # Distressed safety paint: deterministic gaps/scratches, not a plain label.
        for i in range(0,w,36):
            c.create_polygon(i+3,2,i+19,2,i+27,h-2,i+11,h-2,fill=INK,outline='')
        for i in range(17,w,53):
            c.create_line(i,4,i+7,4,fill=INK,width=1)
            c.create_line(i+12,h-5,i+29,h-5,fill='#655C3A',width=2)

    def open_video(self):
        path=filedialog.askopenfilename(title='Wczytaj film',filetypes=[('Filmy','*.mp4 *.mov *.avi *.mkv *.m4v'),('Wszystkie','*.*')])
        if path:self.load_path(path)

    def load_path(self,path):
        cap=cv2.VideoCapture(str(path))
        if not cap.isOpened():messagebox.showerror('PROTOVID','Nie można otworzyć filmu.');return False
        n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps=float(cap.get(cv2.CAP_PROP_FPS))
        if n<1 or fps<=0:
            cap.release();messagebox.showerror('PROTOVID','Niepoprawna liczba klatek lub FPS.');return False
        self.playing=False
        if self.cap:self.cap.release()
        self.path=str(path);self.cap=cap;self.frames=n;self.fps=fps
        self.width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));self.height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.pos=0;self.masks=[];self.selected=-1;self.segments=[(0,n)]
        self.timeline.configure(to=n-1);self.refresh_masks();self.refresh_parts();self.seek(0)
        self.status_text.set('ZAŁADOWANO  •  '+Path(path).name)
        return True

    def seek(self,idx):
        if self.cap is None:return
        idx=max(0,min(self.frames-1,int(idx)))
        self.pos=idx;self.cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
        ok,fr=self.cap.read()
        if ok:
            self.raw=fr;self.render()
        self._suppress=True;self.timeline.set(idx);self._suppress=False
        self.frame_text.set(f'{idx/self.fps:07.2f}s / {self.frames/self.fps:07.2f}s  |  {idx+1} / {self.frames}')

    def slider_move(self,val):
        if not self._suppress:self.seek(int(float(val)))

    def toggle_play(self):
        if not self.cap:return
        self.playing=not self.playing
        if self.playing:self.play_mark=time.monotonic()-self.pos/self.fps;self.play_tick()

    def play_tick(self):
        if not self.playing or not self.cap:return
        target=min(self.frames-1,int((time.monotonic()-self.play_mark)*self.fps))
        if target!=self.pos:self.seek(target)
        if target>=self.frames-1:self.playing=False
        else:self.root.after(15,self.play_tick)

    def render(self):
        if not hasattr(self,'raw') or self.raw is None:return
        frame=apply_masks(self.raw,self.masks,self.pos)
        H,W=frame.shape[:2];cw=max(1,self.canvas.winfo_width());ch=max(1,self.canvas.winfo_height())
        scale=min(cw/W,ch/H); dw=max(1,round(W*scale));dh=max(1,round(H*scale))
        ox=(cw-dw)//2;oy=(ch-dh)//2;self.canvas_geometry=(scale,ox,oy)
        rgb=cv2.cvtColor(cv2.resize(frame,(dw,dh),interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR),cv2.COLOR_BGR2RGB)
        self.photo=ImageTk.PhotoImage(Image.fromarray(rgb))
        c=self.canvas;c.delete('all');c.create_image(ox,oy,image=self.photo,anchor='nw',tags='video')
        for j,m in enumerate(self.masks):
            if not m.enabled or not m.first<=self.pos<=m.last:continue
            x,y,w,h=m.box_at(self.pos)
            x1=ox+x*scale;y1=oy+y*scale;x2=x1+w*scale;y2=y1+h*scale
            color=YELLOW if j==self.selected else '#FFFFFF'
            c.create_rectangle(x1,y1,x2,y2,outline=color,width=2 if j==self.selected else 1,dash=(5,3))
            c.create_text(x1+4,y1+4,anchor='nw',text=f'{j+1:02} {m.name}',fill=color,font=('Consolas',10,'bold'))
            if j==self.selected:
                for px,py in ((x1,y1),(x2,y1),(x1,y2),(x2,y2)):
                    c.create_rectangle(px-4,py-4,px+4,py+4,fill=YELLOW,outline=INK)
        if self.mouse and self.mouse['kind']=='draw':
            ax,ay=self.mouse['origin'];bx,by=self.mouse['cursor']
            c.create_rectangle(ax,ay,bx,by,outline=YELLOW,width=2,dash=(3,2))

    def source_point(self,event):
        scale,ox,oy=self.canvas_geometry
        return (max(0,min(self.width-1,round((event.x-ox)/scale))),
                max(0,min(self.height-1,round((event.y-oy)/scale))))

    def mouse_down(self,e):
        if not self.cap:return
        x,y=self.source_point(e)
        for i in range(len(self.masks)-1,-1,-1):
            m=self.masks[i]
            if not m.enabled or not m.first<=self.pos<=m.last:continue
            bx,by,bw,bh=m.box_at(self.pos);tol=max(5,int(8/max(0.01,self.canvas_geometry[0])))
            if bx-tol<=x<=bx+bw+tol and by-tol<=y<=by+bh+tol:
                self.select_mask(i)
                corner=None
                for name,px,py in [('nw',bx,by),('ne',bx+bw,by),('sw',bx,by+bh),('se',bx+bw,by+bh)]:
                    if abs(px-x)<=tol and abs(py-y)<=tol:corner=name;break
                self.mouse={'kind':'resize' if corner else 'move','corner':corner,
                            'origin':(x,y),'source_box':(bx,by,bw,bh),'mask':i,'changed':False}
                return
        self.mouse={'kind':'draw','origin':(e.x,e.y),'cursor':(e.x,e.y)}

    def mouse_move(self,e):
        if self.mouse is None:return
        drag=self.mouse
        if drag['kind']=='draw':drag['cursor']=(e.x,e.y);self.render();return
        x,y=self.source_point(e);startx,starty=drag['origin'];bx,by,bw,bh=drag['source_box']
        dx=x-startx;dy=y-starty
        if drag['kind']=='move':
            box=clamp_box((bx+dx,by+dy,bw,bh),self.width,self.height)
        else:
            corner=drag['corner'];x0=bx+dx if 'w' in corner else bx
            y0=by+dy if 'n' in corner else by
            x1=bx+bw+dx if 'e' in corner else bx+bw
            y1=by+bh+dy if 's' in corner else by+bh
            x0,x1=sorted((x0,x1));y0,y1=sorted((y0,y1))
            box=clamp_box((x0,y0,max(8,x1-x0),max(8,y1-y0)),self.width,self.height)
        self.masks[drag['mask']].keys[self.pos]=box;drag['changed']=True
        self.render()

    def mouse_up(self,e):
        if self.mouse is None:return
        drag=self.mouse;self.mouse=None
        if drag['kind']=='draw':
            a,b=self.source_point(type('Point',(),{'x':drag['origin'][0],'y':drag['origin'][1]})())
            c,d=self.source_point(e)
            x=min(a,c);y=min(b,d);w=abs(a-c);h=abs(b-d)
            if w>=10 and h>=10:self.new_mask((x,y,w,h))
        elif drag.get('changed'):
            self.status_text.set(f'KOREKTA ZAPISANA  •  KLATKA {self.pos+1}')
        self.render()

    def new_mask(self,box):
        name=f'MASKA {len(self.masks)+1:02}'
        m=Mask(name,tuple(box),first=self.pos,last=self.frames-1)
        m.keys[self.pos]=tuple(box)
        self.masks.append(m);self.refresh_masks();self.select_mask(len(self.masks)-1);self.render()

    def add_center_mask(self):
        if self.cap is None:return
        w=max(30,self.width//6);h=max(30,self.height//6)
        self.new_mask(((self.width-w)//2,(self.height-h)//2,w,h))

    def delete_mask(self):
        if self.selected<0:return
        self.masks.pop(self.selected);self.selected=-1;self.refresh_masks();self.render()

    def refresh_masks(self):
        self.masklist.delete(0,'end')
        for m in self.masks:
            self.masklist.insert('end',f'[{"X" if m.enabled else " "}] {m.name}  |  {m.strength:03}')
        if 0<=self.selected<len(self.masks):self.masklist.selection_set(self.selected)

    def mask_selected(self,e):
        if self._suppress:return
        sel=self.masklist.curselection()
        if sel:self.select_mask(sel[0])

    def select_mask(self,idx):
        if not 0<=idx<len(self.masks):return
        self.selected=idx;m=self.masks[idx]
        self._suppress=True
        self.masklist.selection_clear(0,'end');self.masklist.selection_set(idx)
        self.strength.set(m.strength);self.strength_label.set(f'SIŁA ROZMYCIA    {m.strength} / 100')
        self.mode.set(m.mode);self.enabled.set(m.enabled)
        self.first.set(str(m.first+1));self.last.set(str(m.last+1))
        self._suppress=False;self.render()

    def property_changed(self,*args):
        if self._suppress or self.selected<0:return
        m=self.masks[self.selected];m.strength=self.strength.get();m.mode=self.mode.get();m.enabled=self.enabled.get()
        self.strength_label.set(f'SIŁA ROZMYCIA    {m.strength} / 100')
        self.refresh_masks();self.render()

    def range_changed(self,e=None):
        if self._suppress or self.selected<0:return
        try:
            first=max(1,min(self.frames,int(self.first.get())))-1
            last=max(first+1,min(self.frames,int(self.last.get())))-1
        except ValueError:
            self.select_mask(self.selected);return
        m=self.masks[self.selected];m.first=first;m.last=last;self.select_mask(self.selected)

    def add_key(self):
        if self.selected<0:return
        m=self.masks[self.selected];m.keys[self.pos]=m.box_at(self.pos)
        self.status_text.set(f'KLATKA KLUCZOWA ZAPISANA  •  {self.pos+1}')
        self.render()

    def detect_faces(self):
        if self.cap is None:return
        cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
        faces=cascade.detectMultiScale(cv2.cvtColor(self.raw,cv2.COLOR_BGR2GRAY),scaleFactor=1.1,minNeighbors=5)
        for x,y,w,h in faces:self.new_mask((int(x),int(y),int(w),int(h)))
        self.status_text.set(f'WYKRYTO TWARZE  •  {len(faces)}')

    def track(self,reverse):
        if self.selected<0 or self.cap is None or self.task:return
        mask_i=self.selected;mask=copy.deepcopy(self.masks[mask_i]);begin=self.pos
        end=mask.first if reverse else min(mask.last,self.frames-1)
        if begin==end:self.status_text.set('ŚLEDZENIE  •  ZMIEŃ POZYCJĘ KLATKI');return
        def worker():
            try:
                result=track_range(self.path,mask,begin,end,callback=lambda p:self.events.put(('progress',p)))
                self.events.put(('track_done',(mask_i,result)))
            except Exception as exc:self.events.put(('error',str(exc)))
        self.task=threading.Thread(target=worker,daemon=True);self.task.start()
        self.status_text.set('ŚLEDZENIE W TOKU...')

    def fmt(self,idx):return f'{idx/self.fps:.2f}s'

    def refresh_parts(self,selected=None):
        self._suppress=True
        self.partlist.delete(*self.partlist.get_children())
        for j,(a,b) in enumerate(self.segments):
            self.partlist.insert('', 'end',iid=str(j),values=(f'{j+1:02}',self.fmt(a),self.fmt(b),self.fmt(b-a)))
        if selected is not None and 0<=selected<len(self.segments):self.partlist.selection_set(str(selected))
        self._suppress=False

    def part_selected(self,e):
        if self._suppress:return
        sel=self.partlist.selection()
        if sel:self.seek(self.segments[int(sel[0])][0])

    def cut_here(self):
        if self.cap is None:return
        prev=len(self.segments);new=split_segment(self.segments,self.pos)
        self.segments=new;self.refresh_parts()
        if len(new)>prev:self.status_text.set(f'CIĘCIE  •  KLATKA {self.pos+1}')
        else:self.status_text.set('PRZESUŃ GŁOWICĘ WEWNĄTRZ FRAGMENTU')

    def move_part(self,step):
        sel=self.partlist.selection()
        if not sel:return
        j=int(sel[0]);k=j+step
        if not 0<=k<len(self.segments):return
        self.segments[j],self.segments[k]=self.segments[k],self.segments[j]
        self.refresh_parts(k)

    def delete_part(self):
        sel=self.partlist.selection()
        if not sel:return
        j=int(sel[0]);self.segments.pop(j);self.refresh_parts(min(j,len(self.segments)-1))


    def save_project(self):
        if self.cap is None:return
        path=filedialog.asksaveasfilename(title='Zapisz projekt PROTOVID',defaultextension='.protovid.json',
             filetypes=[('Projekt PROTOVID','*.protovid.json')],initialfile=Path(self.path).stem+'.protovid.json')
        if not path:return
        payload={'format':'PROTOVID-1','source':self.path,'segments':self.segments,
                 'masks':[{'name':m.name,'base':m.base,'strength':m.strength,'mode':m.mode,
                           'enabled':m.enabled,'first':m.first,'last':m.last,
                           'keys':{str(k):v for k,v in m.keys.items()},
                           'tracked':{str(k):v for k,v in m.tracked.items()}} for m in self.masks]}
        try:
            with open(path,'w',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
            self.status_text.set('PROJEKT ZAPISANY  •  '+Path(path).name)
        except Exception as exc:messagebox.showerror('PROTOVID',str(exc))

    def open_project(self):
        path=filedialog.askopenfilename(title='Otwórz projekt PROTOVID',
              filetypes=[('Projekt PROTOVID','*.protovid.json'),('JSON','*.json')])
        if not path:return
        try:
            with open(path,encoding='utf-8') as f:p=json.load(f)
            if p.get('format')!='PROTOVID-1':raise ValueError('Nieobsługiwany format projektu.')
            source=p['source']
            if not Path(source).exists():
                source=filedialog.askopenfilename(title='Wskaż film źródłowy projektu')
                if not source:return
            if not self.load_path(source):return
            segments=[tuple(map(int,seg)) for seg in p['segments']]
            if any(a<0 or b>self.frames or a>=b for a,b in segments):
                raise ValueError('Projekt zawiera niepoprawne przedziały klatek.')
            masks=[]
            for v in p['masks']:
                m=Mask(str(v['name']),tuple(v['base']),strength=int(v['strength']),mode=v['mode'],
                       enabled=bool(v['enabled']),first=int(v['first']),last=int(v['last']))
                m.keys={int(k):tuple(box) for k,box in v['keys'].items()}
                m.tracked={int(k):tuple(box) for k,box in v['tracked'].items()}
                masks.append(m)
            self.masks=masks;self.segments=segments;self.refresh_masks();self.refresh_parts();self.seek(0)
            self.status_text.set('PROJEKT OTWARTY  •  '+Path(path).name)
        except Exception as exc:messagebox.showerror('PROTOVID',f'Nie można otworzyć projektu:\n{exc}')

    def export(self):
        if self.cap is None or self.task:return
        if not self.segments:messagebox.showwarning('PROTOVID','Nie ma fragmentów do wyeksportowania.');return
        target=filedialog.asksaveasfilename(title='Zapisz film',defaultextension='.mp4',
                 filetypes=[('Film MP4','*.mp4')],initialfile=Path(self.path).stem+'_PROTOVID.mp4')
        if not target:return
        if Path(target).resolve()==Path(self.path).resolve():
            messagebox.showwarning('PROTOVID','Wybierz inną nazwę niż plik źródłowy.');return
        snapshot=copy.deepcopy(self.masks);parts=list(self.segments);audio=self.audio.get()
        self.progress['value']=0
        def worker():
            try:
                result=export_video(self.path,target,snapshot,parts,keep_audio=audio,
                                    callback=lambda n:self.events.put(('progress',n)))
                self.events.put(('export_done',result))
            except Exception as exc:self.events.put(('error',str(exc)))
        self.task=threading.Thread(target=worker,daemon=True);self.task.start()
        self.status_text.set('EKSPORT W TOKU  •  H.264')

    def poll_events(self):
        try:
            while True:
                typ,payload=self.events.get_nowait()
                if typ=='progress':self.progress['value']=payload
                elif typ=='track_done':
                    i,boxes=payload
                    if 0<=i<len(self.masks):self.masks[i].tracked.update(boxes)
                    self.task=None;self.render();self.status_text.set(f'ŚLEDZENIE ZAKOŃCZONE  •  {len(boxes)} KLATEK')
                elif typ=='export_done':
                    self.task=None;self.status_text.set('EKSPORT GOTOWY  •  '+Path(payload['path']).name)
                    messagebox.showinfo('PROTOVID',f'Film zapisany:\n{payload["path"]}\n\nKlatki: {payload["frames"]}\nDźwięk: {"TAK" if payload["audio"] else "NIE"}')
                elif typ=='error':
                    self.task=None;self.status_text.set('BŁĄD  •  SPRAWDŹ KOMUNIKAT')
                    messagebox.showerror('PROTOVID',payload)
        except queue.Empty:pass
        self.root.after(60,self.poll_events)

    def close(self):
        if self.task and self.task.is_alive():
            messagebox.showwarning('PROTOVID','Trwa przetwarzanie. Zakończ je przed zamknięciem.');return
        self.playing=False
        if self.cap:self.cap.release()
        self.root.destroy()


def main():
    root=tk.Tk();ProToVid(root);root.mainloop()

if __name__=='__main__':main()
