# Docker 入门实战笔记

> 来源：[技术爬爬虾《40分钟的Docker实战攻略》](https://www.bilibili.com/video/BV1THKyzBER6/) · 视频时长 39:28  
> 按完整视频讲解和章节画面整理，参考评论区笔记。示例采用本机端口；标为“补充”的内容已核对官方文档。整理日期：2026-11-14。

**学习主线**：认识镜像 → 运行容器 → 保存数据 → 排查问题 → 制作镜像 → 用 Compose 管理多个容器。

| 章节 | 回看视频 |
| --- | --- |
| [[#1. 先分清三个概念]] | [00:00](https://www.bilibili.com/video/BV1THKyzBER6/?t=0) |
| [[#2. 安装与验证]] | [01:20](https://www.bilibili.com/video/BV1THKyzBER6/?t=80) |
| [[#3. 下载镜像]] | [04:09](https://www.bilibili.com/video/BV1THKyzBER6/?t=249) |
| [[#4. 启动第一个容器]] | [09:33](https://www.bilibili.com/video/BV1THKyzBER6/?t=573) |
| [[#5. 挂载：把数据留在容器外]] | [13:01](https://www.bilibili.com/video/BV1THKyzBER6/?t=781) |
| [[#6. 其他常用启动参数]] | [16:56](https://www.bilibili.com/video/BV1THKyzBER6/?t=1016) |
| [[#7. 查看、启停与调试]] | [19:34](https://www.bilibili.com/video/BV1THKyzBER6/?t=1174) |
| [[#8. Dockerfile：制作自己的镜像]] | [24:45](https://www.bilibili.com/video/BV1THKyzBER6/?t=1485) |
| [[#9. 容器之间怎样通信]] | [29:16](https://www.bilibili.com/video/BV1THKyzBER6/?t=1756) |
| [[#10. Compose：用一个文件管理多个服务]] | [33:31](https://www.bilibili.com/video/BV1THKyzBER6/?t=2011) |

## 1. 先分清三个概念

| 概念            | 通俗理解                    | 例子                |
| ------------- | ----------------------- | ----------------- |
| 镜像 Image      | 做糕点的模具，包含应用及其运行所需的文件、依赖 | `nginx:1.28.0`    |
| 容器 Container  | 用模具做出的糕点，是镜像创建出的运行实例    | 一个正在运行的 Nginx     |
| 镜像仓库 Registry | 存放、下载和分享模具的地方           | Docker Hub、私有镜像仓库 |

![镜像、容器与 Dockerfile 的关系](assets/01-image-container.png)

一个镜像可以创建多个容器。容器停止后仍然存在，可以再次启动；镜像也不会跟着消失。

**容器与虚拟机的区别**：虚拟机有自己的完整操作系统内核；同一台 Linux Docker 主机上的容器共享内核，因此通常更轻、启动更快。Mac／Windows 的 Docker Desktop 会通过 Linux 环境运行 Linux 容器。[官方说明](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)

## 2. 安装与验证

| 系统 | 视频中的安装思路 |
| --- | --- |
| Linux | 安装 Docker Engine；普通用户可能需要在命令前加 `sudo` |
| Windows | 启用 WSL 2／虚拟机平台，再安装 Docker Desktop |
| Mac | 安装 Docker Desktop；Apple 芯片选 ARM64，Intel 芯片选 x86_64 |

你目前用的是 Mac，按 [Docker 官方 Mac 安装说明](https://docs.docker.com/desktop/setup/install/mac-install/) 下载对应版本，安装后启动 Docker Desktop。

```bash
# 查看客户端与服务端版本
# 同时出现 Client 和 Server 信息，才说明已连上 Docker 引擎
docker version

docker compose version
```

出现 `Cannot connect to the Docker daemon`，先确认 Docker Desktop 已启动。只运行 `docker --version` 只能确认命令行工具存在。

## 3. 下载镜像

```bash
docker pull nginx:1.28.0    # 下载指定标签
docker images               # 查看本地镜像
docker rmi nginx:1.28.0      # 删除本地镜像；不等于删除容器
```

完整名称这样拆：

```text
docker.io / library / nginx : 1.28.0
仓库地址    命名空间   镜像名    标签
```

`docker.io/library/` 在这个例子中可以省略。一个 Registry 中有很多 Repository；例如 `library/nginx` 是一个镜像库，可以包含多个标签。

**补充**：不写标签时默认使用 `latest`，但 `latest` 只是一个标签名，**不保证版本最新，也不会让已经运行的容器自动更新**。复现教程时写明标签更稳妥。[镜像引用](https://docs.docker.com/engine/containers/run/#image-references)

**下载超时**：视频通过镜像加速解决网络问题。Linux 配置位置是 `/etc/docker/daemon.json`；Desktop 中是 Settings → Docker Engine。镜像站地址会变化，查看 [UP 主维护的安装与加速资料](https://github.com/tech-shrimp/docker_installer)，修改时合并原配置，不要直接覆盖整份 JSON。

**架构不匹配**：优先让 Docker 自动选择本机架构；遇到 `no matching manifest` 再核对镜像支持的平台。ARM Mac 必须使用 AMD64 镜像时，可指定 `--platform linux/amd64`，但需要模拟支持，可能更慢。

## 4. 启动第一个容器

```bash
docker run -d --name web -p 127.0.0.1:8080:80 nginx:1.28.0
```

浏览器打开 **http://localhost:8080**，应看到 Nginx 欢迎页。

| 参数 | 含义 |
| --- | --- |
| `run` | 从镜像创建并启动一个新容器；本地没有镜像时默认先拉取 |
| `-d` | 后台运行，不占用当前终端 |
| `--name web` | 容器叫 `web`，同一 Docker 引擎中不能重名 |
| `-p 127.0.0.1:8080:80` | 只在本机发布端口：宿主机 `8080` → 容器 `80` |
| `nginx:1.28.0` | 使用的镜像，放在启动选项之后 |

![端口映射与目录绑定](assets/02-ports-bind.png)

**记忆法**：`-p 外部端口:内部端口`，先外后内。上图省略了 `127.0.0.1`；命令中加上它，是把这个练习的访问范围限制在本机。[运行参数](https://docs.docker.com/engine/containers/run/)

## 5. 挂载：把数据留在容器外

**停止容器不会删除文件；删除容器会删除其可写层。** 想让数据在容器删除、重建后还存在，就把对应目录挂载出去。

![容器可写层、绑定挂载和命名卷](assets/03-data-lifecycle.png)

### 5.1 绑定挂载：自己指定目录

在一个练习目录中执行，以下命令适用于 Mac／Linux：

```bash
mkdir -p html
printf '<h1>Hello Docker</h1>\n' > html/index.html

docker run -d --name web-files \
  -p 127.0.0.1:8082:80 \
  -v "$(pwd)/html:/usr/share/nginx/html:ro" \
  nginx:1.28.0
```

打开 **http://localhost:8082**。修改本机 `html/index.html` 后刷新页面，就能看到变化。`:ro` 表示容器只能读取这个目录；你仍然可以从本机编辑它。

**视频里的 403 原因**：把一个空目录挂到 Nginx 网页目录后，原来的欢迎页被挂载内容遮住了。先准备 `index.html` 就能避免这种情况；原文件没有被这个操作删除。[绑定挂载说明](https://docs.docker.com/engine/storage/bind-mounts/)

### 5.2 命名卷：让 Docker 管理存储

```bash
docker volume create nginx_html

docker run -d --name web-volume \
  -p 127.0.0.1:8083:80 \
  -v nginx_html:/usr/share/nginx/html \
  nginx:1.28.0

docker volume ls
docker volume inspect nginx_html
```

命名卷适合数据库等持久数据。**空卷第一次挂到有文件的目录时，默认会复制该目录中的已有文件到卷里**；非空卷不会每次重新同步。[卷的行为](https://docs.docker.com/engine/storage/volumes/)

Mac 上 `inspect` 显示的存储路径通常位于 Docker 的 Linux 虚拟机中，不要当作 Finder 中的普通目录直接打开。

## 6. 其他常用启动参数

| 参数 | 作用 | 适合的场景 |
| --- | --- | --- |
| `-e KEY=value` | 给容器传入环境变量 | 账号、连接地址等配置；变量名由镜像文档定义 |
| `-it` | 保持标准输入并分配终端 | 交互调试 |
| `--rm` | 容器退出后自动删除容器 | 用完即走的临时任务 |
| `--restart unless-stopped` | 退出后按策略重启，保留手动停止的状态 | 长期运行的服务 |

```bash
# 临时启动一个轻量 Linux 环境；exit 后删除这个临时容器
docker run --rm -it alpine:3.22 sh
```

**补充**：手动 `stop` 后，`always` 也不会立刻把容器拉起。区别在于 Docker 引擎重启后，`always` 会再次拉起它，`unless-stopped` 会保留停止状态。主机断电期间当然无法重启容器。[重启策略](https://docs.docker.com/engine/containers/start-containers-automatically/)

## 7. 查看、启停与调试

下面继续操作第 4 节的 `web` 容器：

```bash
docker ps                       # 只看正在运行的容器
docker ps -a                    # 包括已停止的容器

docker stop web                 # 停止已有容器
docker start web                # 启动已有容器，沿用原端口、挂载等配置

docker logs --tail 50 -f web     # 最近 50 行日志，并持续跟踪
docker inspect web              # 查看端口、挂载、网络等详细信息

docker exec -it web sh          # 进入运行中的 web 容器
```

进入后可执行 `cat /etc/os-release` 查看系统，执行 `exit` 返回宿主机。容器中不一定有 `bash`、`vim`、`ps` 等工具，不能因为提示“命令不存在”就判断容器坏了。

**三个操作分清楚**：

- `run`：创建新容器；`start`：启动旧容器；`exec`：在运行中的容器里执行命令。
- `rm`：删除容器；`rmi`：删除镜像。删除 `web` 时，先 `docker stop web`，再 `docker rm web`。
- 临时进入容器改文件可以调试；需要长期保留的改动应写入挂载目录，或写成 Dockerfile 重新构建。

**底层理解**：Namespace 负责隔离“进程能看到什么”，cgroups 负责管理、限制资源。容器本质上仍是进程；资源上限需要配置，不会因为用了 Docker 就自动拥有严格的 CPU／内存限额。[资源限制说明](https://docs.docker.com/engine/containers/resource_constraints/)

## 8. Dockerfile：制作自己的镜像

视频用 FastAPI 程序演示：**准备运行环境 → 安装依赖 → 启动程序**。Dockerfile 就是把这些步骤写成可重复执行的制作说明。[Dockerfile 指令](https://docs.docker.com/build/concepts/dockerfile/)

![视频中的 Dockerfile 示例](assets/video-dockerfile.png)

*视频画面：约 27:05，展示构建时安装依赖与容器启动命令。下方为可复制的整理版。*

项目结构：

```text
fastapi-app/
├── main.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

`main.py`：

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello Docker"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

`requirements.txt` 两行：

```text
fastapi
uvicorn
```

`Dockerfile`：

```dockerfile
FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

EXPOSE 8000
CMD ["python", "main.py"]
```

`.dockerignore`：

```text
.git
.venv
__pycache__
*.pyc
.env
```

| 指令 | 什么时候发生 | 作用 |
| --- | --- | --- |
| `FROM`、`WORKDIR`、`COPY`、`RUN` | 构建镜像时 | 选基础镜像、设工作目录、复制文件、安装依赖 |
| `CMD` | 启动容器时 | 指定默认启动命令；多次写时只有最后一个生效 |
| `EXPOSE` | 描述镜像 | 提示服务端口，**不会自动发布宿主机端口** |

在 `fastapi-app` 目录中执行：

```bash
docker build -t hello-api:1.0 .
docker run -d --name hello-api -p 127.0.0.1:8000:8000 hello-api:1.0
```

访问 **http://localhost:8000**，应返回 `{"message":"Hello Docker"}`。末尾的 `.` 是构建上下文；本例从这个目录取文件。程序监听 `0.0.0.0`，才能接收转发到容器网卡的请求。

先复制依赖清单再复制程序，是相对视频的一个小优化：只改程序时，更容易复用安装依赖的构建缓存。

分享镜像只需三步，将 `yourname` 换成自己的 Docker Hub 用户名：

```bash
docker login
docker tag hello-api:1.0 yourname/hello-api:1.0
docker push yourname/hello-api:1.0
```

## 9. 容器之间怎样通信

| 网络          | 特点                           |
| ----------- | ---------------------------- |
| 默认 `bridge` | 容器有自己的网络；容器间通常按 IP 通信        |
| 自定义 bridge  | 同一网络中可用容器名／别名通信，适合关联服务       |
| `host`      | 共享 Docker 主机的网络命名空间，`-p` 不生效 |
| `none`      | 不连接外部网络，仍有自己的回环接口            |
|             |                              |

```bash
docker network ls
docker network create app-net
docker network connect app-net web
```

**重点**：容器之间访问“服务名＋容器端口”；浏览器访问“宿主机地址＋发布端口”。不必为了两个容器互相通信，就把数据库端口发布到宿主机。[自定义 bridge 与 DNS](https://docs.docker.com/engine/network/drivers/bridge/)

**Mac 补充**：先用 bridge 学习。视频中的 host 示例在 Linux 上演示；Docker Desktop 4.34 及以后可在设置中启用 host networking，但支持范围与 Linux 主机有区别。[host 网络说明](https://docs.docker.com/engine/network/drivers/host/)

## 10. Compose：用一个文件管理多个服务

**Dockerfile 解决“镜像怎么做”，Compose 解决“多个服务怎么一起运行”。** 视频使用 MongoDB＋mongo-express：一个容器存数据，一个容器提供网页管理界面。

![视频中 docker run 与 Compose 的对应关系](assets/video-compose.png)

*视频画面：约 35:18。`-e` 对应 `environment`，`-v` 对应 `volumes`，`-p` 对应 `ports`。*

![网页管理端访问 MongoDB 的网络路径](assets/04-compose-network.png)

在一个独立目录中创建 `compose.yaml`。下面保留课程的两服务结构，增加命名卷和数据库健康检查：

```yaml
services:
  mongo:
    image: mongo:8.0
    environment:
      MONGO_INITDB_ROOT_USERNAME: demo
      MONGO_INITDB_ROOT_PASSWORD: demo-pass
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test:
        - CMD-SHELL
        - >-
          mongosh --quiet -u demo -p demo-pass
          --authenticationDatabase admin
          --eval "db.adminCommand('ping')"
      interval: 5s
      timeout: 5s
      retries: 20

  admin:
    image: mongo-express:1.0.2
    ports:
      - "127.0.0.1:8081:8081"
    environment:
      ME_CONFIG_MONGODB_URL: mongodb://demo:demo-pass@mongo:27017/?authSource=admin
      ME_CONFIG_BASICAUTH_USERNAME: viewer
      ME_CONFIG_BASICAUTH_PASSWORD: viewer-pass
    depends_on:
      mongo:
        condition: service_healthy

volumes:
  mongo_data:
```

在文件所在目录执行：

```bash
docker compose config --quiet    # 先检查配置语法
docker compose up -d             # 创建网络、卷和容器，然后启动
docker compose ps
docker compose logs --tail 50 -f # 跟踪各服务日志
```

浏览器打开 **http://localhost:8081**，网页登录是 `viewer / viewer-pass`；数据库账号是 `demo / demo-pass`，两套账号用途不同。完整文件也放在本笔记旁的 `实操示例/mongo-compose/` 中。

理解这份文件，只抓住四点：

1. Compose 为这个项目创建默认网络，`admin` 用服务名 **`mongo:27017`** 找到数据库。这里若写 `localhost`，指向的是 `admin` 自己。
2. 数据库没有 `ports`，仍能被同网络中的 `admin` 访问；它的数据写入 `mongo_data` 卷。
3. 普通 `depends_on` 只保证启动顺序；这里结合健康检查，等数据库就绪后才启动网页端。[就绪与启动的区别](https://docs.docker.com/compose/how-tos/startup-order/)
4. 服务名不是实际容器名。Compose 通常生成“项目名－服务名－序号”，日常用 `docker compose logs admin` 这样的服务级命令即可。[Compose 入门](https://docs.docker.com/compose/gettingstarted/)

```bash
docker compose stop             # 只停止
docker compose start            # 再次启动已存在的容器
docker compose down             # 停止并删除容器和项目网络，保留命名卷
docker compose -f other.yaml up -d  # 指定其他文件
```

**保留数据**：`down` 默认保留命名卷；`down -v` 会额外删除这里声明的卷及其中数据。[down 的行为](https://docs.docker.com/reference/cli/docker/compose/down/)

**版本补充（2026-11 核对）**：视频使用的 Docker Hub `mongo-express` 镜像目前已标为停止维护。这里固定 `1.0.2` 用于本机复习课程；新项目需重新选择维护中的管理工具或自行构建，见 [镜像状态](https://hub.docker.com/_/mongo-express)。

## 常见问题速查

| 现象 | 先检查什么 |
| --- | --- |
| 容器名已被占用 | `docker ps -a`；旧容器用 `start`，新实验换名字 |
| `port is already allocated` | 宿主机端口被占用；只改 `-p` 左侧的端口 |
| 网页打不开 | `docker ps -a` → `docker logs` → 端口映射 → 程序是否监听 `0.0.0.0` |
| 改了代码，容器仍是旧行为 | 重新 `build`，再重建容器；单纯 `start` 不会更新镜像 |
| 修改数据库环境变量后密码没变 | 初始化变量通常只在空数据目录首次启动时使用；旧卷中的账号不会因此重置 |

## 资料与实操文件

- [原视频及评论区](https://www.bilibili.com/video/BV1THKyzBER6/)：主要学习来源。
- [评论区分享的笔记](https://www.bilibili.com/read/cv42531657/)：一键AI笔记侠，评论编号 `270940020720`；已阅读其长图，作为提纲核对，未直接照搬。
- [UP 主安装与镜像加速仓库](https://github.com/tech-shrimp/docker_installer)：查看更新后的安装／网络资料。
- [MongoDB 镜像文档](https://github.com/docker-library/docs/blob/master/mongo/README.md)、[mongo-express 环境变量](https://github.com/mongo-express/mongo-express-docker#configuration)：账号与连接参数的依据。
- 本地 `实操示例/`：包含 FastAPI 镜像示例、MongoDB Compose 示例和 Nginx 网页。文件已经做语法检查；本机尚未实际启动这些容器。
