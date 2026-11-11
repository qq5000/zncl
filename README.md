# 智能唱练评测批量代练工作台 (zncl)

基于 Web API 纯学号接口直连的智能唱练评测批量自动完成与 AI 评分平台。

## ✨ 项目核心特性

- **纯账号密码直连**：彻底摆脱对微信 OpenID 的依赖，不需要微信扫码或复制链接，100% 独立稳定。
- **全学段年级曲目库适配**：收录小学 **三、四、五、六 年级** 对应教材（人教版、接力版、湘艺版）全量官方曲目。
- **学号智能识别**：粘贴 Excel 学号整列时，自动识别年级代码（如 `08624...` -> 三年级，`08623...` -> 四年级）并联动曲目库。
- **录音自适应高保真转码**：内置 FFmpeg，完美支持手机端录音（`.m4a`）、电脑端音频（`.mp3`/`.wav`/`.aac` 等）自动转码为标准 128kbps 双声道音频。
- **独立管理员后台**：提供安全密码验证后台（默认密码 `6531684`），支持一键上传并重命名音频，前台老师即选即测。
- **脱机任务守护与断点恢复**：后端独立子线程执行，无论刷新网页还是重新打开浏览器，打卡进度与日志均完整保留。
- **换班重置与清理缓存**：支持同一台手机/电脑完成一个班级后一键清空状态并刷新会话，无缝接力下一个班级。
- **完全响应式 UI**：移动端手机竖屏与电脑宽屏双端自适应优化排版。

---

## 🐂 飞牛私有云 (fnOS) / Docker Compose 极简部署

飞牛 NAS 用户可以直接打开 **Docker 界面 -> Compose / 项目 -> 新建项目**，将以下 YAML 内容直接复制粘贴进去，点击“创建”即可启动：

### 飞牛 NAS Compose 配置模板
```yaml
version: '3.8'

services:
  zncl:
    # 镜像地址：将 <你的GitHub用户名> 替换为您 GitHub 上的实际用户名（例如 ghcr.io/zhangsan/zncl:latest）
    # 若在飞牛本地直接构建，亦可将 image 换为 build: .
    image: ghcr.io/<你的GitHub用户名>/zncl:latest
    container_name: zncl_app
    restart: always
    ports:
      - "8080:8080"
    environment:
      - ZNCL_PORT=8080
      - ZNCL_ADMIN_PASSWORD=6531684   # 管理员后台密码（按需修改）
      - ZNCL_ORGCODE=blspzzzxxx       # 学校机构代码（默认即可）
    volumes:
      # 持久化存储目录：飞牛 NAS 上的存储路径，确保录音文件与元数据重启不丢失
      - ./uploads:/app/web/uploads
      - ./audio_meta.json:/app/web/audio_meta.json
```

> 💡 **飞牛使用提示**：
> 1. 端口映射 `8080:8080`：如飞牛 NAS 上 8080 端口已被其他容器占用，可修改为其他外部端口（如 `8088:8080`）；
> 2. 音频持久化卷：挂载了 `./uploads` 目录后，老师在后台上传并重命名的所有示范录音都会稳妥保存在飞牛的硬盘上，容器升级或重启不会丢失。

---

## 🚀 自动化构建与发布 Docker 镜像 (GitHub Actions)

项目已为您配置好 **GitHub Actions 全自动流水线**（`.github/workflows/docker-publish.yml`）：
- 只要您将代码推送到 GitHub 的 `main` 分支，GitHub 云端服务器就会**全自动构建并生成 Docker 镜像并发布到 GitHub Packages (ghcr.io)**！
- 飞牛 NAS 或任何 Linux 服务器直接拉取该镜像即可运行：
```bash
# 拉取您发布在 GitHub 上的镜像（将 username 换为您的 GitHub 用户名）
docker pull ghcr.io/<username>/zncl:latest

# 直接运行容器
docker run -d \
  --name zncl_app \
  -p 8080:8080 \
  -v /vol1/1000/docker/zncl/uploads:/app/web/uploads \
  --restart always \
  ghcr.io/<username>/zncl:latest
```

---

## 🐳 本地 Docker 手动构建与运行 (适用于有 Docker 的电脑或服务器)
```bash
# 1. 本地构建镜像 zncl
docker build -t zncl:latest .

# 2. 运行容器
docker run -d \
  --name zncl_app \
  -p 8080:8080 \
  -v $(pwd)/web/uploads:/app/web/uploads \
  --restart always \
  zncl:latest
```

或在项目目录下直接执行：
```bash
docker-compose up -d
```

启动完成后，打开浏览器访问：
- **前台工作台**：`http://<飞牛或服务器IP>:8080`
- **管理员后台**：`http://<飞牛或服务器IP>:8080/admin`（默认管理密码：`6531684`）

---

### 方式二：Python 本地直接运行

#### 环境要求
- Python 3.10+
- 系统安装有 `ffmpeg`（如不需要本地 m4a 转码可忽略）

#### 运行步骤
```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
python web/app.py
```

访问 `http://localhost:8080` 即可开始使用。

---

## ⚙️ 环境变量配置

可根据部署需要自定义以下环境变量：

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `ZNCL_PORT` | `8080` | Web 服务监听端口 |
| `ZNCL_ADMIN_PASSWORD` | `6531684` | 管理员后台访问密码 |
| `ZNCL_ORGCODE` | `blspzzzxxx` | 默认学校机构代码 |

---

## 📂 项目结构

```text
zncl/
├── Dockerfile                  # Docker 镜像构建文件（生成 zncl 镜像）
├── docker-compose.yml          # Docker Compose 编排文件
├── requirements.txt            # Python 依赖清单
├── README.md                   # 项目使用说明文档
├── .gitignore                  # Git 忽略文件
├── grade_songs.json            # 3-6年级全版本官方曲目元数据
└── web/
    ├── app.py                  # FastAPI 主服务（API 与任务调度）
    ├── static/
    │   ├── index.html          # 前台工作台页面（响应式）
    │   └── admin.html          # 管理员后台页面
    └── uploads/                # 音频文件存储目录（支持卷挂载）
```

---

## 📄 免责声明与许可

本项目仅供教研自动化测试及学习交流使用，严禁用于任何商业牟利及非法用途。使用者因使用本项目所产生的任何行为后果均由使用者自行承担。
