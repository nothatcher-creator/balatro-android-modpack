from pathlib import Path
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

assert 'io.open(destPath,"wb")' not in main.read_text()
assert 'love.filesystem.createDirectory(AI_RUNTIME_DIR)' in main.read_text()
assert 'local VERSION = "0.5.0-ai-alpha3"' in main.read_text()
print('alpha3 runtime patch applied')
