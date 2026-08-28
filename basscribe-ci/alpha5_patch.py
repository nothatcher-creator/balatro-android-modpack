from pathlib import Path
root=Path('/tmp/basscribe-alpha5/basscribe_alpha4')

def rw(rel, old, new):
    p=root/rel; s=p.read_text()
    if old not in s: raise SystemExit(f'missing patch target: {rel}')
    p.write_text(s.replace(old,new))

# Version/package names.
for rel in ['game/main.lua','native/basscribe_ai.cpp','build_android.sh']:
    p=root/rel; p.write_text(p.read_text().replace('0.5.0-ai-alpha4','0.5.0-ai-alpha5'))

rw('game/main.lua', '''                        local art=notes[i].articulation
                        if art and sd==0 then c=c-1.35 end
                        if art and sd>0 then c=c+3.75 end
                        if (art=="hammer" or art=="pull") and sd==0 and math.abs(p.fret-q.fret)<=5 then c=c-0.85 end
                        if art=="slide" and sd==0 then c=c-0.65 end
''', '''                        local art=notes[i].articulation
                        -- Articulation is evidence, not permission to wreck an otherwise natural fingering.
                        if (art=="hammer" or art=="pull") then
                            if sd==0 and math.abs(p.fret-q.fret)<=5 then c=c-1.15 else c=c+1.85 end
                        elseif art=="slide" then
                            if sd==0 and math.abs(p.fret-q.fret)<=5 then c=c-0.45
                            elseif sd>0 then c=c+0.75 end
                        end
''')

rw('game/main.lua', '''    -- First, make legato destinations use the same physical string whenever
    -- the interval is playable there. That makes h/p/slide notation match how
    -- a bassist would actually execute it instead of jumping strings.
    for i=2,#notes do
        local p,n=notes[i-1],notes[i]
        if n.eventKind=="legato" then
            local delta=n.midi-p.midi
            if not n.articulation then
                if math.abs(delta)<=4 then n.articulation=(delta>0) and "hammer" or ((delta<0) and "pull" or nil)
                elseif delta~=0 then n.articulation="slide" end
            end
            if p.string then
                local fret=n.midi-OPEN_MIDI[p.string]
                if fret>=0 and fret<=24 and math.abs(fret-(p.fret or fret))<=7 then
                    n.string=p.string; n.fret=fret
                end
            end
        end
    end
''', '''    -- Validate articulations after fingering. Never overwrite a natural position just to satisfy a noisy technique label.
    for i=2,#notes do
        local p,n=notes[i-1],notes[i]
        local delta=n.midi-p.midi
        if not n.articulation and n.eventKind=="legato" then
            if math.abs(delta)<=4 and p.string==n.string then
                n.articulation=(delta>0) and "hammer" or ((delta<0) and "pull" or nil)
            elseif delta~=0 and p.string==n.string and math.abs((n.fret or 0)-(p.fret or 0))<=5 then
                n.articulation="slide"
            end
        end
        if n.articulation then
            local sameString=p.string and n.string and p.string==n.string
            local fretDelta=math.abs((n.fret or 0)-(p.fret or 0))
            if (n.articulation=="hammer" or n.articulation=="pull") and (not sameString or fretDelta>5) then
                n.articulation=nil; n.eventKind="attack"
            elseif n.articulation=="slide" and (not sameString or fretDelta>5) then
                n.articulation=nil; n.eventKind="attack"
            end
        end
    end
''')

p=root/'game/main.lua'; s=p.read_text(); marker='\n-- Basscribe v0.5 neural backend'
insert='''\n\nlocal function collapseDisplayEvents(notes)\n    if #notes < 2 then return notes end\n    table.sort(notes,function(a,b)\n        local at=a.displayTime or a.time or 0; local bt=b.displayTime or b.time or 0\n        if math.abs(at-bt)<0.0005 then return (a.time or 0)<(b.time or 0) end\n        return at<bt\n    end)\n    local out={}\n    local function score(n)\n        local c=tonumber(n.confidence) or 0; local o=tonumber(n.onset) or 0\n        local d=math.min(0.30,tonumber(n.duration) or 0)\n        return c*0.62+o*0.32+d*0.20\n    end\n    for _,n in ipairs(notes) do\n        local p=out[#out]\n        if p then\n            local nt=n.displayTime or n.time or 0; local pt=p.displayTime or p.time or 0\n            local rawGap=(n.time or nt)-(p.time or pt)\n            local sameSlot=math.abs(nt-pt)<=0.018\n            local micro=rawGap>=0 and rawGap<0.070 and ((n.onset or 0)<0.54 or (p.onset or 0)<0.54)\n            if sameSlot or micro then\n                local keepN=score(n)>score(p)+0.035\n                local start=math.min(p.time or pt,n.time or nt)\n                local finish=math.max((p.time or pt)+(p.duration or 0),(n.time or nt)+(n.duration or 0))\n                if keepN then n.time=start; n.duration=math.max(0.06,finish-start); n.displayTime=math.min(pt,nt); out[#out]=n\n                else p.time=start; p.duration=math.max(p.duration or 0,finish-start); p.displayTime=math.min(pt,nt); p.confidence=math.max(p.confidence or 0,n.confidence or 0); p.onset=math.max(p.onset or 0,n.onset or 0) end\n            else out[#out+1]=n end\n        else out[#out+1]=n end\n    end\n    return out\nend\n'''
if marker not in s: raise SystemExit('missing neural marker')
s=s.replace(marker,insert+marker,1); p.write_text(s)

rw('game/main.lua', '''        state.measureDuration=240/state.bpm
        layoutPositions(notes)
        applyArticulations(notes)
        quantizeDisplayTimes(notes)

        state.notes=notes
''', '''        state.measureDuration=240/state.bpm
        quantizeDisplayTimes(notes)
        notes=collapseDisplayEvents(notes)
        layoutPositions(notes)
        applyArticulations(notes)

        state.notes=notes
''')

rw('game/main.lua', '''    local fretFont=(measureNoteCount>=11) and fonts.small or fonts.fret
    local lastDrawX={}
''', '''    local fretFont=(measureNoteCount>=7) and fonts.small or fonts.fret
''')
rw('game/main.lua', '''            local si=note.string or 1
            if lastDrawX[si] and nx-lastDrawX[si] < tw+5 then nx=lastDrawX[si]+tw+5 end
            nx=math.min(nx,staffR-tw/2-2)
            lastDrawX[si]=nx
''', '''            nx=clamp(nx,staffX+tw/2+2,staffR-tw/2-2)
''')
rw('game/main.lua','drawChip(string.format("%d notes",#state.notes),margin+chipW+gap,top+8,chipW,false)','drawChip(string.format("%d clean notes",#state.notes),margin+chipW+gap,top+8,chipW,false)')

rw('native/basscribe_ai.cpp', '''            if (std::abs(n.midi-p.midi)==1 && n.duration<0.10 && n.onset<0.24f && gap<0.04) {
                p.duration=std::max(p.duration,(n.time+n.duration)-p.time);
                p.confidence=std::max(p.confidence,n.confidence*0.95f);
                continue;
            }
''', '''            if (std::abs(n.midi-p.midi)==1 && n.duration<0.11 && n.onset<0.30f && gap<0.05) {
                p.duration=std::max(p.duration,(n.time+n.duration)-p.time);
                p.confidence=std::max(p.confidence,n.confidence*0.95f);
                continue;
            }
            if (n.time-p.time<0.070 && (n.onset<0.54f || p.onset<0.54f)) {
                const float ps=0.62f*p.confidence+0.38f*p.onset, ns=0.62f*n.confidence+0.38f*n.onset;
                if (ns>ps+0.04f) { const double start=std::min(p.time,n.time), finish=std::max(p.time+p.duration,n.time+n.duration); n.time=start; n.duration=std::max(0.06,finish-start); p=n; }
                else { p.duration=std::max(p.duration,(n.time+n.duration)-p.time); p.confidence=std::max(p.confidence,n.confidence); p.onset=std::max(p.onset,n.onset); }
                continue;
            }
''')

bench=root/'benchmarks/gold'; bench.mkdir(parents=True,exist_ok=True)
(bench/'californication-intro-user-reference.json').write_text('''{"title":"Californication","artist":"Red Hot Chili Peppers","tempo_bpm":96,"time_signature":"4/4","source":"user-supplied reference screenshot, 2026-08-28","measures":[{"measure":1,"notes":["D7","D7","G9","G9","G7","G9","G7","D10"]},{"measure":2,"notes":["A8","A8","G7","G7","D10"]},{"measure":3,"notes":["D7","D7","G9","G9","G7","G9","G7","D10"]}]}\n''')
print('alpha5 patch applied')
