# cpp-interview-lab

这是一个用于整理 C++ 面试知识点的笔记仓库，内容按难度分层，适合用于：

- 面试前系统复习
- 八股题速查
- 代码示例回顾
- 扩展为你自己的题库或 training notebook

## 文档入口

- [中文总览](./docs/zh/index.md)
- [初级篇](./docs/zh/beginner.md)
- [中级篇](./docs/zh/intermediate.md)
- [高级篇](./docs/zh/advanced.md)
- [手写代码题](./docs/zh/coding-round.md)
- [C++17 / C++20 高频特性](./docs/zh/modern-cpp.md)
- [STL 容器速查表](./docs/zh/stl-container-cheatsheet.md)
- [并发专题](./docs/zh/concurrency-deep-dive.md)
- [项目回答模板](./docs/zh/project-answer-templates.md)

## 现有结构

- 初级：语法基础、对象模型入门、引用与指针、STL 基础
- 中级：拷贝控制、移动语义、模板、智能指针、并发基础
- 高级：完美转发、内存模型、类型萃取、对象切片、现代 C++ 设计
- 手写代码题：字符串、链表、LRU、线程安全队列
- 现代 C++：`optional`、`variant`、`string_view`、`span`、`concepts`
- STL 速查：复杂度、内存布局、迭代器失效、容器选型
- 并发专题：`mutex`、`atomic`、条件变量、线程池、`future`、内存序
- 项目回答模板：把八股题连接到真实项目表达

## 备注

- 英文版旧文档仍保留在 [docs/cpp-interview-notebook.md](./docs/cpp-interview-notebook.md)
- 中文版会更适合作为长期维护的面试笔记主线

## Flash Card 学习站

如果你想把 `beginner.md` 当成卡片站来复习，可以直接启动本地 webserver：

```bash
python3 tools/flashcards_app.py
```

然后打开浏览器访问 `http://127.0.0.1:8000/`。

这个页面会把每一道题拆成独立页面，默认先显示问题，点击按钮后再展开答案。
每个 notebook 还有题号网格快速跳转、今日访问高亮、以及 `SAVE` 收藏区。
题目页里还可以直接写 `My Note`，支持文字和粘贴截图/图片，内容会持久化到 `./data/`。

它也带了 iPhone 可安装的网页应用配置：
- 在 iPhone Safari 里打开页面
- 点分享按钮，选择“添加到主屏幕”
- 之后可以像独立 app 一样从桌面启动

注意：如果你用的是局域网 `http://<ip>:8000`，iOS 仍然可以添加到主屏幕，但真正的 service worker 缓存和更完整的 PWA 体验通常需要 `HTTPS` 或 `localhost`。如果你需要离线/更完整的 app 体验，建议再套一层 HTTPS 反代。

## Docker 部署

仓库里已经补了可同时支持 `x86_64/amd64` 和 `arm64` 的容器配置。
容器会把浏览记录和收藏状态写到 `./data/flashcards-state.json`，通过 bind mount 保存在容器外。

### 本地构建

```bash
docker build -t cpp-interview-lab:latest .
```

### x86 电脑

```bash
docker compose -f docker-compose.yml -f docker-compose.x86.yml up --build
```

### Raspberry Pi 5

```bash
docker compose -f docker-compose.yml -f docker-compose.arm.yml up --build
```

然后打开 `http://127.0.0.1:8000/`。

如果你要推送多架构镜像，可以用 `buildx`：

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t your-name/cpp-interview-lab:latest --push .
```

如果你想在容器里直接读本地改动，可以额外加一个 bind mount：

```bash
docker run --rm -p 8000:8000 -u "$(id -u):$(id -g)" -v "$PWD":/app -v "$PWD/data":/data cpp-interview-lab:latest
```

### 快速启动

```bash
make server
make docker-up-lan
make docker-up-x86
make docker-up-arm
```

`make docker-up-lan` 会根据机器架构自动选择 `amd64` 或 `arm64` 配置，并通过 `0.0.0.0:8000` 对局域网开放访问。
