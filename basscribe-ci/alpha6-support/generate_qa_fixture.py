import math, struct, wave
from pathlib import Path

SR=44100
OUT=Path(__file__).with_name('qa_pitch_fixture.wav')
# Short monophonic bass regression. First two F2 notes have a deliberately
# dominant octave harmonic; old alpha5 could label this neighborhood as C3.
SEQ=[
    (41,0.58,True), (None,0.12,False),
    (41,0.58,True), (None,0.12,False),
    (48,0.58,False), (None,0.12,False),
    (45,0.58,False), (None,0.12,False),
    (52,0.58,False), (None,0.12,False),
]
frames=[]
for midi,dur,hard in SEQ:
    n=int(SR*dur)
    if midi is None:
        frames.extend([0]*n)
        continue
    f=440.0*2**((midi-69)/12)
    for i in range(n):
        t=i/SR
        attack=min(1.0,t/0.012)
        release=min(1.0,(dur-t)/0.05) if dur-t<0.05 else 1.0
        env=attack*release*math.exp(-0.35*t)
        if hard:
            v=(0.20*math.sin(2*math.pi*f*t)+
               0.92*math.sin(2*math.pi*2*f*t)+
               0.34*math.sin(2*math.pi*3*f*t))
        else:
            v=(0.72*math.sin(2*math.pi*f*t)+
               0.26*math.sin(2*math.pi*2*f*t)+
               0.12*math.sin(2*math.pi*3*f*t))
        frames.append(max(-32767,min(32767,int(v*env*18000))))
with wave.open(str(OUT),'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    for s in frames: w.writeframesraw(struct.pack('<hh',s,s))
print(OUT)
