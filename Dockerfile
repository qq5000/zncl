# 使用轻量级 Python 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装 ffmpeg（用于手机录音 m4a 等格式的高保真自动转码）及基础依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    ZNCL_PORT=8080 \
    ZNCL_ADMIN_PASSWORD=6531684

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝项目源码与年级曲目数据
COPY grade_songs.json .
COPY web/ ./web/

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["python", "web/app.py"]
