# -*- coding: utf-8 -*-
"""
智能唱练评测 (ZNCL) - 纯学号直连多会话隔离 Web 后端服务
============================================================
特点：
1. 完整收录三、四、五、六年级各版本教材（人教版、接力版、湘艺版）全量曲目
2. 根据输入学号自动智能识别年级（08624.../08623.../08622.../08621...）
3. 纯 Web HTTP 接口上传音频与提交 AI 评分，100% 独立稳定，零微信依赖
4. 管理员后台维护音频资产，支持 M4A/MP3 自动转码，前台即选即测
5. 任务后台脱机稳定运行，页面刷新无损恢复进度与全量日志
6. 响应式布局自适应手机移动端与电脑端
"""

import os
import sys
import time
import json
import ssl
import random
import threading
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="zncl - 智能唱练评测批量工作台")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
GRADE_SONGS_FILE = os.path.join(PROJECT_ROOT, "grade_songs.json")
AUDIO_META_FILE = os.path.join(BASE_DIR, "audio_meta.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://imusic.ixzds.com/imusic/imusic/component/sing/sing_main.html",
    "Origin": "https://imusic.ixzds.com",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# 加载全量年级曲目库
ALL_GRADE_DATA = {}
if os.path.exists(GRADE_SONGS_FILE):
    with open(GRADE_SONGS_FILE, "r", encoding="utf-8") as f:
        ALL_GRADE_DATA = json.load(f)

DEFAULT_ORGCODE = os.environ.get("ZNCL_ORGCODE", "blspzzzxxx")
ADMIN_PASSWORD = os.environ.get("ZNCL_ADMIN_PASSWORD", "6531684")

# 基础主会话令牌（系统在底层自动维护保活）
GLOBAL_TOKEN = (
    "gJb2R6StpTJ4WUA3of2V0LibL4hxSQBj1ELycDdvyu3ueLOIDy7SoQZhgmfAk6WnSEEyno10qyYG\n"
    "QkCUc0avWDxewixYff031s8chxqYyMG4kJb5QP7wYfIaZJZsrZ7mEuTXQOvFI7xSxyxKpO3AM9QS\n"
    "KkBBeJOmrDhsDvN14YYNa3ja96/PwsYkJhvfwsZAX6OWHn+T0poE+9kqooUa9rDsf5oN2Kv2UK/E\n"
    "2QxWqZ5rU1Kk/9k923N6H68F8w6qF4bUf+Tj4x8c=="
)
LAST_TOKEN_REFRESH = time.time()

# 存储各教师会话的任务状态
SESSION_TASKS: Dict[str, Dict[str, Any]] = {}


def post_api(url: str, data: dict, timeout: int = 15) -> dict:
    post_bytes = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=post_bytes, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text)
    except Exception as e:
        return {"result": 0, "msg": str(e)}


def get_token_keepalive() -> str:
    global GLOBAL_TOKEN, LAST_TOKEN_REFRESH
    if time.time() - LAST_TOKEN_REFRESH > 600 or not GLOBAL_TOKEN:
        url = "https://imusic.ixzds.com/imusicdd/HttpChannel?action=WEBSITE_ACTION&BUSINESS_TYPE=imusic.login!getToken"
        params = {
            "PERSON_ID": "P46bf0f45e5ea4aa8841",
            "ORGCODE": DEFAULT_ORGCODE,
            "SESSION_OPNAME": "",
            "token": GLOBAL_TOKEN
        }
        res = post_api(url, params)
        if res.get("result") == 1:
            data = res.get("data")
            if isinstance(data, str):
                data = json.loads(data)
            GLOBAL_TOKEN = data.get("token", GLOBAL_TOKEN)
            LAST_TOKEN_REFRESH = time.time()
    return GLOBAL_TOKEN


def upload_audio_bytes(audio_bytes: bytes, orgcode: str, mp3_name: str = "rec.mp3") -> dict:
    boundary = "----WebKitFormBoundary" + hex(int(time.time() * 1000))[2:]
    fields = {
        "groupid": f"vocal_sc_score_{int(time.time() * 1000)}",
        "appid": "imusiczk_vocal",
        "mp3Name": mp3_name,
        "orgcode": orgcode,
        "dir_str": f"personSing/{orgcode}"
    }

    body_parts = []
    for k, v in fields.items():
        body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8"))

    file_header = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{mp3_name}\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode("utf-8")
    body_parts.append(file_header + audio_bytes + b"\r\n")
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    payload = b"".join(body_parts)

    headers = dict(HEADERS)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    req = urllib.request.Request("https://file.ixzds.com/file/upload", data=payload, headers=headers)
    with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") == 1 or "attachid" in data:
            return {"attachid": data["attachid"], "path": data["path"]}
        raise RuntimeError(f"音频上传失败: {data}")


@app.get("/api/grades_and_songs")
def get_grades_and_songs():
    """返回所有年级的结构化曲目库列表供前端联动下拉"""
    return {"success": True, "data": ALL_GRADE_DATA}


@app.post("/api/upload_custom_audio")
async def upload_custom_audio(file: UploadFile = File(...), session_id: str = Form(...)):
    raw_ext = os.path.splitext(file.filename)[1].lower()
    base_name = f"{session_id}_{int(time.time())}"
    raw_filename = f"{base_name}{raw_ext}"
    raw_path = os.path.join(UPLOAD_DIR, raw_filename)
    
    with open(raw_path, "wb") as f:
        f.write(await file.read())

    # 如果是 .m4a, .aac, .wav, .ogg, .flac 等格式，自动通过 ffmpeg 转为标准 128k MP3
    final_filename = raw_filename
    if raw_ext in [".m4a", ".aac", ".wav", ".ogg", ".flac", ".wma", ".webm"]:
        mp3_filename = f"{base_name}.mp3"
        mp3_path = os.path.join(UPLOAD_DIR, mp3_filename)
        try:
            cmd = [
                "ffmpeg", "-y", "-i", raw_path,
                "-acodec", "libmp3lame", "-ab", "128k", "-ar", "44100", "-ac", "2",
                mp3_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(mp3_path):
                final_filename = mp3_filename
        except Exception as e:
            print("Audio transcode error:", e)

    return {"success": True, "filename": final_filename, "orig_filename": file.filename}


class StartTaskReq(BaseModel):
    session_id: str
    grade: str # "三年级", "四年级", "五年级", "六年级"
    students: List[Dict[str, str]]
    required_song_id: str
    required_song_name: str
    custom_audio: str # 必须提供音频
    orgcode: Optional[str] = DEFAULT_ORGCODE


def run_worker_thread(session_id: str, req: StartTaskReq):
    state = SESSION_TASKS[session_id]
    state["is_running"] = True
    state["is_finished"] = False
    state["completed"] = 0
    state["total"] = len(req.students)

    def log(msg: str, color: str = "#e2e8f0"):
        state["logs"].append({"msg": msg, "color": color})

    log(f"任务启动：准备为【{req.grade}】{len(req.students)} 名学生执行练习评测 (纯接口直连模式)...", "#38bdf8")

    orgcode = req.orgcode or DEFAULT_ORGCODE
    cur_token = get_token_keepalive()

    # 准备真实音频字节流
    audio_path = os.path.join(UPLOAD_DIR, req.custom_audio)
    if not os.path.exists(audio_path):
        state["is_running"] = False
        state["is_finished"] = True
        log(f"❌ 错误：未找到指定的音频文件 ({req.custom_audio})，请重新选择或上传音频后再试！", "#f87171")
        return

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    log(f"✔ 成功加载打卡录音音频 ({len(audio_bytes)//1024} KB)", "#4ade80")

    required_name = req.required_song_name or "中国少年先锋队队歌"

    try:
        for idx, stu in enumerate(req.students):
            acc = stu["account"].strip()
            name = stu["name"].strip()
            pwd = stu.get("pwd", "888888").strip()

            log(f"[{idx+1}/{len(req.students)}] 正在查询学生档案: {name} (学号: {acc})...", "#e2e8f0")

            # 1. 纯接口直连获取学生独立 PERSON_ID 档案号
            bind_url = "https://imusic.ixzds.com/imusicdd/HttpChannel?action=WEBSITE_T_ACTION&BUSINESS_TYPE=imusic.login!bandPhone"
            bind_params = {
                "LOGIN_MODE": 0,
                "USERTYPE": "2",
                "LOGIN_TYPE": "1",
                "WXOPENID": f"student_{acc}",
                "ORGCODE": orgcode,
                "OP_ACCOUNT": acc,
                "PWD": pwd,
                "SUBJECT_TYPE": "music"
            }
            res_bind = post_api(bind_url, bind_params)
            if not ("绑定成功" in str(res_bind.get("result", "")) or "data" in res_bind):
                log(f"  ❌ [{name}] 账号或密码错误，档案获取失败: {res_bind.get('msg', '')}", "#f87171")
                state["records"].append({"account": acc, "name": name, "status": "失败", "songs": "密码/学号错误"})
                state["completed"] += 1
                continue

            person_id = json.loads(res_bind["data"])["PERSON_ID"]

            # 打卡曲目：指定曲目
            songs_to_do = [{"name": required_name, "id": req.required_song_id}]

            done_songs = []
            for song in songs_to_do:
                s_name = song["name"]
                s_id = song["id"]
                try:
                    # 获取曲目
                    detail_url = "https://imusic.ixzds.com/imusic/HttpChannel?action=WEBSITE_ACTION&BUSINESS_TYPE=sing.record!getMusicPo2id"
                    detail_params = {
                        "ORGCODE": orgcode,
                        "PERSON_ID": person_id,
                        "LIBRARY_ID": s_id,
                        "MAX_ANS_NUM": "2",
                        "FROM": "zk",
                        "SESSION_OPNAME": "",
                        "token": cur_token,
                        "USER_NAME": person_id,
                        "interface": "1",
                        "protocol": "https",
                        "SUBJECT_TYPE": "music"
                    }
                    res_det = post_api(detail_url, detail_params)
                    detail = json.loads(res_det.get("data", "{}"))

                    # 上传音频（纯 Web 直传）
                    up = upload_audio_bytes(audio_bytes, orgcode, f"rec_{acc}_{s_id[:6]}.mp3")

                    # 提交答卷与评分（纯接口直连）
                    save_url = "https://imusic.ixzds.com/imusic/HttpChannel?action=WEBSITE_ACTION&BUSINESS_TYPE=sing.record!save"
                    speed = detail.get("SPEED", 1.0)
                    abc_content = detail.get("ABC_CONTENT", "")
                    vocal_json = {
                        "AUDIO_ATTACHID": up["attachid"],
                        "AUDIO_URL": up["path"],
                        "PRAC_COUNT": 1,
                        "PRAC_TIME": random.randint(45, 75),
                        "ABC_CONTENT": abc_content
                    }
                    save_params = {
                        "PERSON_ID": person_id,
                        "LIBRARY_ID": s_id,
                        "USE_TIME": 0,
                        "FILE_NAME": up["path"],
                        "QS_FILE": "",
                        "STAND_ID": "",
                        "ATTACH_ID": up["attachid"],
                        "ABC": abc_content,
                        "OFFSET": 0,
                        "FRE_CHANGE": "",
                        "NEW_SPEED": speed,
                        "SPEED": speed,
                        "ANS_FILE_URL": up["path"],
                        "MUSIC_NAME": s_name,
                        "MUSIC_GROUP": detail.get("QS_OBJECT", ""),
                        "SCORE_TOTAL": 0,
                        "APPID": orgcode,
                        "ORGCODE": orgcode,
                        "SYS_CODE": "",
                        "ANS_GROUP_ID": detail.get("ANS_GROUP_ID") or f"ans_{int(time.time()*1000)}",
                        "VOICE_ATTACH_ID": detail.get("VOICE_ATTACH_ID", ""),
                        "ACCOMPANY_ATTACH_ID": detail.get("ACCOMPANY_ATTACH_ID", ""),
                        "QINGCHANG_ATTACH_ID": "",
                        "VOCAL_JSON": json.dumps(vocal_json, ensure_ascii=False),
                        "SCORE_TYPE": "qiepian",
                        "IS_ONLY_BC": 1,
                        "token": cur_token,
                        "USER_NAME": person_id,
                        "interface": "1",
                        "protocol": "https",
                        "SUBJECT_TYPE": "music"
                    }
                    res_save = post_api(save_url, save_params)
                    if res_save.get("result") == 1:
                        done_songs.append(s_name)
                        log(f"  ✔ [{name}] 成功完成【{req.grade}】曲目《{s_name}》并送交 AI 评分", "#4ade80")
                    else:
                        log(f"  ❌ [{name}] 提交曲目《{s_name}》失败: {res_save}", "#f87171")
                    time.sleep(1.2)
                except Exception as ex:
                    log(f"  ❌ [{name}] 作答异常: {str(ex)}", "#f87171")

            state["records"].append({
                "account": acc,
                "name": name,
                "status": "完成" if len(done_songs) == len(songs_to_do) else "部分完成",
                "songs": ", ".join(done_songs)
            })
            state["completed"] += 1
            time.sleep(1.5)

    finally:
        state["is_running"] = False
        state["is_finished"] = True
        log(f"🎉 【{req.grade}】全员打卡任务执行结束！结果已全部汇总归档。", "#38bdf8")


@app.post("/api/start_task")
def start_task(req: StartTaskReq):
    session_id = req.session_id
    if session_id in SESSION_TASKS and SESSION_TASKS[session_id].get("is_running"):
        return {"success": False, "msg": "当前已有任务正在进行中，请等待其执行完成！"}

    SESSION_TASKS[session_id] = {
        "grade": req.grade,
        "req_info": {
            "required_song_name": req.required_song_name,
            "grade": req.grade
        },
        "logs": [],
        "last_log_idx": 0,
        "records": [],
        "completed": 0,
        "total": len(req.students),
        "is_running": False,
        "is_finished": False
    }

    t = threading.Thread(target=run_worker_thread, args=(session_id, req), daemon=True)
    t.start()
    return {"success": True}


@app.get("/api/task_status")
def task_status(session_id: str):
    if session_id not in SESSION_TASKS:
        return {"has_task": False, "is_finished": False, "completed": 0, "total": 0, "new_logs": [], "all_logs": [], "records": []}
    
    st = SESSION_TASKS[session_id]
    all_logs = st["logs"]
    last_idx = st["last_log_idx"]
    new_logs = all_logs[last_idx:]
    st["last_log_idx"] = len(all_logs)

    return {
        "has_task": True,
        "grade": st.get("grade", ""),
        "req_info": st.get("req_info", {}),
        "is_finished": st.get("is_finished", False),
        "is_running": st.get("is_running", False),
        "completed": st.get("completed", 0),
        "total": st.get("total", 0),
        "new_logs": new_logs,
        "all_logs": all_logs,
        "records": st.get("records", [])
    }


@app.post("/api/clear_session")
def clear_session(req: Dict[str, str]):
    session_id = req.get("session_id")
    if session_id and session_id in SESSION_TASKS:
        if not SESSION_TASKS[session_id].get("is_running"):
            del SESSION_TASKS[session_id]
    return {"success": True}


def get_audio_meta() -> List[Dict[str, Any]]:
    if os.path.exists(AUDIO_META_FILE):
        try:
            with open(AUDIO_META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_audio_meta(items: List[Dict[str, Any]]):
    with open(AUDIO_META_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

class AdminVerifyReq(BaseModel):
    password: str

class AdminDeleteAudioReq(BaseModel):
    id: str
    password: str

@app.post("/api/admin/verify")
def admin_verify(req: AdminVerifyReq):
    if req.password.strip() == ADMIN_PASSWORD:
        return {"success": True}
    return {"success": False, "msg": "管理密码错误！"}

@app.get("/api/public_audios")
def list_public_audios():
    """获取所有已重命名入库的公共音频"""
    items = get_audio_meta()
    valid_items = []
    for it in items:
        p = os.path.join(UPLOAD_DIR, it["filename"])
        if os.path.exists(p):
            it["size"] = os.path.getsize(p)
            valid_items.append(it)
    return {"success": True, "audios": valid_items}

@app.get("/api/audio_file/{filename}")
def stream_audio_file(filename: str):
    p = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(p):
        return FileResponse(p, media_type="audio/mpeg")
    return HTMLResponse("File Not Found", status_code=404)

@app.post("/api/admin/upload_audio")
async def admin_upload_audio(
    file: UploadFile = File(...),
    name: str = Form(...),
    password: str = Form(...)
):
    if password.strip() != ADMIN_PASSWORD:
        return {"success": False, "msg": "密码鉴权失败"}

    raw_ext = os.path.splitext(file.filename)[1].lower()
    audio_id = "aud_" + hex(int(time.time() * 1000))[2:]
    raw_filename = f"{audio_id}{raw_ext}"
    raw_path = os.path.join(UPLOAD_DIR, raw_filename)

    with open(raw_path, "wb") as f:
        f.write(await file.read())

    final_filename = raw_filename
    # 如果不是 mp3，自动调用 ffmpeg 转码为标准 mp3
    if raw_ext in [".m4a", ".aac", ".wav", ".ogg", ".flac", ".wma", ".webm"]:
        mp3_filename = f"{audio_id}.mp3"
        mp3_path = os.path.join(UPLOAD_DIR, mp3_filename)
        try:
            cmd = [
                "ffmpeg", "-y", "-i", raw_path,
                "-acodec", "libmp3lame", "-ab", "128k", "-ar", "44100", "-ac", "2",
                mp3_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(mp3_path):
                final_filename = mp3_filename
        except Exception as e:
            print("Admin audio transcode error:", e)

    meta = get_audio_meta()
    meta.insert(0, {
        "id": audio_id,
        "name": name.strip(),
        "filename": final_filename,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    save_audio_meta(meta)

    return {"success": True, "filename": final_filename}

@app.post("/api/admin/delete_audio")
def admin_delete_audio(req: AdminDeleteAudioReq):
    if req.password.strip() != ADMIN_PASSWORD:
        return {"success": False, "msg": "鉴权失败"}
    meta = get_audio_meta()
    new_meta = []
    for it in meta:
        if it["id"] == req.id:
            try:
                p = os.path.join(UPLOAD_DIR, it["filename"])
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        else:
            new_meta.append(it)
    save_audio_meta(new_meta)
    return {"success": True}

@app.get("/admin")
def get_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

@app.get("/")
def get_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("ZNCL_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
