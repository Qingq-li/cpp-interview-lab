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
- [C++ 版本新特性速查](./docs/zh/cpp_news_versions.md)
- [`std` 标准库学习材料](./docs/zh/std-library.md)

## 现有结构

- 初级：语法基础、对象模型入门、引用与指针、STL 基础
- 中级：拷贝控制、移动语义、模板、智能指针、并发基础
- 高级：完美转发、内存模型、类型萃取、对象切片、现代 C++ 设计
- C++ 版本新特性速查：按 C++11 到 C++23 梳理语言与库特性
- `std` 标准库学习材料：容器、算法、字符串、视图、时间、文件系统、并发工具

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

## 启动方式

### 本地部署

本地有两种入口：

```bash
make server
make docker-up
```

`make server` 直接在宿主机启动，默认绑定 `0.0.0.0:8000`。
`make docker-up` 会根据本机架构自动选择 `amd64` 或 `arm64` 的 compose 覆盖文件。
如果需要停止容器或看日志，可以继续用：

```bash
make docker-down
make docker-logs
```

### 远端单机部署

远端单机部署继续走 Docker Compose，但命令统一成通用的 `remote-*` 入口：

```bash
make remote-sync REMOTE_HOST=<host>
make remote-run REMOTE_HOST=<host>
make remote-tmux REMOTE_HOST=<host>
make remote-install-autostart REMOTE_HOST=<host>
```

默认会同步到远端用户家目录下的 `flashcards/`，远端容器状态仍然写到远端的 `data/` 目录。
如果远端主机端口不是 `8000`，可以通过 `HOST_PORT` 或 `REMOTE_PORT` 覆盖。

### 远端 Kubernetes 部署

仓库里新增了 `k8s/` 下的最小清单，包含 `Namespace`、`PersistentVolumeClaim`、`Deployment` 和 `NodePort Service`。

```bash
make k8s-build K8S_IMAGE=<registry>/cpp-interview-lab:latest
make k8s-push K8S_IMAGE=<registry>/cpp-interview-lab:latest
make k8s-deploy K8S_NAMESPACE=flashcards K8S_IMAGE=<registry>/cpp-interview-lab:latest
make k8s-logs K8S_NAMESPACE=flashcards
make k8s-port-forward K8S_NAMESPACE=flashcards
```

如果集群架构和本机不一致，可以额外指定 `K8S_PLATFORM=linux/amd64` 或 `linux/arm64`。
部署后默认通过 `http://<node-ip>:30080/` 访问，也可以用 `make k8s-port-forward` 本地转发到 `http://127.0.0.1:8000/`。
