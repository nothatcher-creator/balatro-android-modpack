from pathlib import Path
import json, hashlib
root=Path('/tmp/basscribe/Basscribe-v0.5-source')
main=root/'game/main.lua'
s=main.read_text()
s=s.replace('local VERSION = "0.5.0-ai-alpha2"','local VERSION = "0.5.0-ai-alpha3"')
old='''local function ensureModelAsset(assetName, destName, prettyName)
    local info=love.filesystem.getInfo(assetName)
    if not info or not info.size or info.size<1024 then
        error(prettyName.." model is missing from this build.")
    end
    local saveDir=love.filesystem.getSaveDirectory()
    local destPath=saveDir.."/"..destName
    local existing=io.open(destPath,"rb")
    if existing then
        local n=existing:seek("end") or 0; existing:close()
        if n==info.size then return destPath end
    end
    state.status="Preparing neural models..."
    state.detail="Copying "..prettyName.." for first use"
    local src=assert(love.filesystem.newFile(assetName,"r"))
    local dst=assert(io.open(destPath,"wb"))
    local copied=0
    while true do
        local chunk=src:read(1024*1024)
        if not chunk or #chunk==0 then break end
        assert(dst:write(chunk))
        copied=copied+#chunk
        state.progress=0.02+0.04*(copied/math.max(1,info.size))
        coroutine.yield()
    end
    src:close(); dst:close()
    return destPath
end
'''
new='''local AI_RUNTIME_DIR = "ai-runtime"

local function ensureAIRuntimeDir()
    local info=love.filesystem.getInfo(AI_RUNTIME_DIR)
    if info and info.type=="directory" then return end
    local ok,err=love.filesystem.createDirectory(AI_RUNTIME_DIR)
    if not ok then
        error("Could not initialize Basscribe app storage: "..tostring(err or "unknown error"))
    end
end

local function ensureModelAsset(assetName, destName, prettyName)
    local info=love.filesystem.getInfo(assetName)
    if not info or not info.size or info.size<1024 then
        error(prettyName.." model is missing from this build.")
    end
    ensureAIRuntimeDir()
    local destRel=AI_RUNTIME_DIR.."/"..destName
    local destPath=love.filesystem.getSaveDirectory().."/"..destRel
    local existing=love.filesystem.getInfo(destRel)
    if existing and existing.type=="file" and existing.size==info.size then
        return destPath
    end
    pcall(function() love.filesystem.remove(destRel) end)
    state.status="Preparing neural models..."
    state.detail="Copying "..prettyName.." for first use"
    local src,srcErr=love.filesystem.newFile(assetName,"r")
    if not src then error("Could not open embedded "..prettyName.." model: "..tostring(srcErr or "unknown error")) end
    local dst,dstErr=love.filesystem.newFile(destRel,"w")
    if not dst then src:close(); error("Could not create "..prettyName.." runtime model: "..tostring(dstErr or "unknown error")) end
    local copied=0
    local ok,copyErr=pcall(function()
        while true do
            local chunk=src:read(1024*1024)
            if not chunk or #chunk==0 then break end
            local wrote,writeErr=dst:write(chunk)
            if wrote==false or wrote==nil then error(writeErr or "model write failed") end
            copied=copied+#chunk
            state.progress=0.02+0.04*(copied/math.max(1,info.size))
            coroutine.yield()
        end
    end)
    src:close(); dst:close()
    if not ok then
        pcall(function() love.filesystem.remove(destRel) end)
        error("Could not prepare "..prettyName.." model: "..tostring(copyErr))
    end
    local finalInfo=love.filesystem.getInfo(destRel)
    if not finalInfo or finalInfo.type~="file" or finalInfo.size~=info.size then
        pcall(function() love.filesystem.remove(destRel) end)
        error(prettyName.." model copy was incomplete ("..tostring(copied).." of "..tostring(info.size).." bytes).")
    end
    return destPath
end
'''
assert old in s, 'alpha2 ensureModelAsset block not found'
s=s.replace(old,new)
needle='''        local wavRel="basscribe_ai_input.wav"
        local resultRel="basscribe_ai_result.csv"'''
assert needle in s, 'alpha2 runtime file block not found'
s=s.replace(needle,'''        ensureAIRuntimeDir()
        local wavRel=AI_RUNTIME_DIR.."/basscribe_ai_input.wav"
        local resultRel=AI_RUNTIME_DIR.."/basscribe_ai_result.csv"''')
main.write_text(s)

p=root/'build_android.sh'; s=p.read_text()
s=s.replace('app.version_code=51','app.version_code=52')
s=s.replace('app.version_name=0.5.0-ai-alpha2','app.version_name=0.5.0-ai-alpha3')
s=s.replace('Basscribe-v0.5.0-ai-alpha2-arm64.apk','Basscribe-v0.5.0-ai-alpha3-arm64.apk')
p.write_text(s)

p=root/'CHANGELOG.md'; p.write_text('''# Basscribe v0.5.0-ai-alpha3\n\n- Fixed first-run Android model extraction: neural model files are now copied through LÖVE filesystem storage instead of raw `io.open()`.\n- Added an explicit `ai-runtime/` save directory and verified model-copy size before native inference starts.\n- Moved temporary analysis WAV/CSV files into the same initialized runtime directory.\n- Improves model-copy errors so a storage failure reports the actual failing stage instead of a generic analysis failure.\n\n'''+p.read_text())
p=root/'IMPLEMENTATION_STATUS.md'; p.write_text(p.read_text().replace('Implemented in this package:', 'Implemented in this package:\n\n- alpha3 Android first-run save-directory/model extraction fix'))

manifest={
  'version':1,
  'note':'Exact user-supplied regression corpus pinned by SHA-256. Audio/PDF binaries are intentionally not redistributed in source.',
  'songs':[
    {'id':'californication','artist':'Red Hot Chili Peppers','title':'Californication','audio_file':'Californication_48UPSzbZjgc449aqz8bxox.mp3','audio_sha256':'ae2f54f109e1cf605423a21787019b0d2155abc1d0324c9de3bd767450b6f0bd','audio_duration_seconds':329.900408,'reference_pdf':'Red Hot Chili Peppers - Californication.pdf','reference_pdf_sha256':'4c09c78bff269f1c55947ff60d6e6d2adfdffdd84091ab0d4533d392722b4f06','reference_pages':7,'reference_measures':128,'reference_tempo_bpm':96},
    {'id':'the-less-i-know-the-better','artist':'Tame Impala','title':'The Less I Know The Better','audio_file':'The Less I Know The Better_6K4t31amVTZDgR3sKmwUJJ.mp3','audio_sha256':'ff6499a455141e21421da6ebbace13071eea963ad0b8b434be508164da17382d','audio_duration_seconds':217.443265,'reference_pdf':'Tame Impala - The Less I Know The Better.pdf','reference_pdf_sha256':'3692439989e71a3c1c354595656f691aa8104e06fba122ad9e9cdbd14735ccba','reference_pages':5,'reference_measures':105,'reference_tempo_bpm':117},
    {'id':'number-of-the-beast','artist':'Iron Maiden','title':'The Number of the Beast - 2015 Remaster','audio_file':'The Number of the Beast - 2015 Remaster_3nlGByvetDcS1uomAoiBmy.mp3','audio_sha256':'1791e7171b79e73ac565574cb71b9f41b989e3bd21e86cbca4e9f45fd4969f1e','audio_duration_seconds':290.951837,'reference_pdf':'Iron Maiden - The Number Of The Beast.pdf','reference_pdf_sha256':'8e4d01978a94c8b759f1cf83305a87d93deee8071e0fb183ea36d1ee0b6f295f','reference_pages':12,'reference_measures':209,'reference_tempo_bpm':198}
  ]
}
(root/'benchmarks/reference-corpus.json').write_text(json.dumps(manifest,indent=2)+'\n')
p=root/'benchmarks/README.md'
p.write_text(p.read_text()+'''\n## Locked user benchmark corpus\n\n`reference-corpus.json` pins the exact three MP3s and three Songsterr PDF references supplied for Basscribe testing by SHA-256, along with duration, page count, measure count and reference tempo. The copyrighted audio/PDF binaries are not bundled in the source archive.\n''')

# Contract checks that specifically guard the alpha2 crash from returning.
assert 'io.open(destPath,"wb")' not in main.read_text()
assert 'love.filesystem.createDirectory(AI_RUNTIME_DIR)' in main.read_text()
assert 'local VERSION = "0.5.0-ai-alpha3"' in main.read_text()
print('alpha3 patch applied')
