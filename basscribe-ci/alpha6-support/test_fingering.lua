BASSCRIBE_TEST=true
love={}
dofile("game/main.lua")
local T=assert(BasscribeTest)
local notes={}
local midis={45,45,52,52,50,52,50,48, 41,41,50,50,48}
for i,m in ipairs(midis) do
    notes[i]={midi=m,time=(i-1)*0.30,duration=0.22,confidence=0.9}
end
T.layoutPositions(notes)
local expected={
    {3,7},{3,7},{4,9},{4,9},{4,7},{4,9},{4,7},{3,10},
    {2,8},{2,8},{4,7},{4,7},{3,10},
}
for i,e in ipairs(expected) do
    local n=notes[i]
    assert(n.string==e[1] and n.fret==e[2],
        string.format("note %d midi %d: got string=%s fret=%s expected string=%d fret=%d",
            i,n.midi,tostring(n.string),tostring(n.fret),e[1],e[2]))
end
print("californication fingering regression: PASS")
