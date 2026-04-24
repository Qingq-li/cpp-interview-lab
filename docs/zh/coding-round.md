# C++ 面试笔记：手写代码题

这一篇整理高频手写题。每题都包含：

- 题目描述
- 面试官常看点
- 标准思路
- 代码实现
- 常见追问

---

## 1. 反转字符串

### 题目描述

给定一个字符串，将其原地反转。


### English explanation

In an English interview, I would say:

Given a string, reverse it in place.

### 面试官常看点

- 是否能写出双指针
- 是否考虑空串和单字符串
- 是否能说清时间复杂度和空间复杂度

### 标准思路

使用左右两个指针向中间收缩，逐步交换字符。

### 代码实现

```cpp
#include <algorithm>
#include <iostream>
#include <string>

void reverseString(std::string& s) {
    int left = 0;
    int right = static_cast<int>(s.size()) - 1;

    while (left < right) {
        std::swap(s[left], s[right]);
        ++left;
        --right;
    }
}

int main() {
    std::string s = "hello";
    reverseString(s);
    std::cout << s << '\n';
}
```

### 常见追问

- 如果字符串是 UTF-8 怎么办
- 能不能不用 `std::swap`
- 如果要求返回新字符串而不是原地修改怎么写

### 补充理解

- 这题的核心是双指针，不是调用库函数
- 时间复杂度是 O(n)，空间复杂度是 O(1)
- 如果字符串里是多字节编码字符，按字节反转可能破坏字符边界，这时问题就不再是简单字符串题

---

## 2. 判断字符串是否为回文

### 题目描述

判断一个字符串是否为回文串。


### English explanation

In an English interview, I would say:

Determine whether a string is a palindrome.

### 面试官常看点

- 边界处理
- 双指针是否写得干净
- 是否会继续扩展到忽略大小写和非字母字符

### 标准思路

从两端向中间比较，只要有一对字符不相等就返回 `false`。

### 代码实现

```cpp
#include <iostream>
#include <string>

bool isPalindrome(const std::string& s) {
    int left = 0;
    int right = static_cast<int>(s.size()) - 1;

    while (left < right) {
        if (s[left] != s[right]) {
            return false;
        }
        ++left;
        --right;
    }

    return true;
}

int main() {
    std::cout << isPalindrome("level") << '\n';
    std::cout << isPalindrome("hello") << '\n';
}
```

### 常见追问

- 忽略空格和标点怎么做
- 忽略大小写怎么做
- 如果数据量很大，是否要提前拷贝预处理

### 补充理解

- 最基础版本只考双指针和边界条件
- 如果题目要求忽略非字母字符，通常仍然可以保持 O(1) 额外空间
- 面试里最好主动说明空串、单字符串也应返回 true

---

## 3. 实现单链表反转

### 题目描述

给定单链表头节点，返回反转后的头节点。


### English explanation

In an English interview, I would say:

Given the head node of a singly linked list, return the reversed head node.

### 面试官常看点

- 指针操作是否清晰
- 是否考虑空链表和单节点
- 是否能解释为什么不会丢链

### 标准思路

维护 `prev`、`cur`、`next` 三个指针，逐个翻转链接方向。

### 代码实现

```cpp
#include <iostream>

struct ListNode {
    int val;
    ListNode* next;
    explicit ListNode(int v) : val(v), next(nullptr) {}
};

ListNode* reverseList(ListNode* head) {
    ListNode* prev = nullptr;
    ListNode* cur = head;

    while (cur != nullptr) {
        ListNode* next = cur->next;
        cur->next = prev;
        prev = cur;
        cur = next;
    }

    return prev;
}
```

### 常见追问

- 递归版本怎么写
- 双链表反转有什么不同
- 如何避免内存泄漏

### 补充理解

- 这题最容易错在指针修改顺序，必须先保存 `next`
- 时间复杂度 O(n)，空间复杂度 O(1)
- 如果是手写裸节点题，通常不涉及创建和释放节点，重点是正确改链

---

## 4. 找链表中间节点

### 题目描述

返回单链表的中间节点。


### English explanation

In an English interview, I would say:

Returns the middle node of a singly linked list.

### 面试官常看点

- 是否能想到快慢指针
- 偶数长度时返回前中点还是后中点

### 标准思路

快指针每次走两步，慢指针每次走一步。快指针到尾时，慢指针在中间。

### 代码实现

```cpp
struct ListNode {
    int val;
    ListNode* next;
    explicit ListNode(int v) : val(v), next(nullptr) {}
};

ListNode* middleNode(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;

    while (fast != nullptr && fast->next != nullptr) {
        slow = slow->next;
        fast = fast->next->next;
    }

    return slow;
}
```

### 常见追问

- 如何判断链表是否有环
- 如何找到环的入口

### 补充理解

- 快慢指针是链表题核心套路之一
- 如果链表长度为偶数，返回前中点还是后中点要看循环条件写法
- 面试里能把“为什么 slow 停在中间”讲清楚，通常比背答案更重要

---

## 5. 合并两个有序链表

### 题目描述

输入两个递增链表，合并成一个递增链表并返回头节点。


### English explanation

In an English interview, I would say:

Input two increasing linked lists, merge them into one increasing linked list and return the head node.

### 面试官常看点

- 是否写出 dummy 节点
- 边界是否稳定
- 是否会分析复杂度

### 标准思路

使用哑节点 `dummy`，逐步比较两个链表当前节点，小的接到结果链表后面。

### 代码实现

```cpp
struct ListNode {
    int val;
    ListNode* next;
    explicit ListNode(int v) : val(v), next(nullptr) {}
};

ListNode* mergeTwoLists(ListNode* l1, ListNode* l2) {
    ListNode dummy(0);
    ListNode* tail = &dummy;

    while (l1 != nullptr && l2 != nullptr) {
        if (l1->val < l2->val) {
            tail->next = l1;
            l1 = l1->next;
        } else {
            tail->next = l2;
            l2 = l2->next;
        }
        tail = tail->next;
    }

    tail->next = (l1 != nullptr) ? l1 : l2;
    return dummy.next;
}
```

### 常见追问

- 递归写法怎么写
- k 个有序链表怎么合并

### 补充理解

- dummy 节点的价值是统一头节点处理逻辑，减少分支
- 这题时间复杂度 O(m + n)，空间复杂度 O(1)，如果不算输入节点本身
- 很多链表题都适合先引入 dummy，再处理尾指针推进

---

## 6. 实现 LRU Cache

### 题目描述

设计一个支持 `get` 和 `put` 的 LRU，要求平均 O(1)。


### English explanation

In an English interview, I would say:

Design an LRU that supports `get` and `put`, requiring average O(1).

### 面试官常看点

- 是否知道哈希表 + 双向链表
- 是否能解释为什么是 O(1)
- 是否会把更新、淘汰、搬到头部这些操作拆清楚

### 标准思路

- 哈希表：`key -> 链表节点`
- 双向链表：维护最近使用顺序
- 访问或更新时把节点移到头部
- 超容量时淘汰尾部节点

### 代码实现

```cpp
#include <unordered_map>

class LRUCache {
private:
    struct Node {
        int key;
        int value;
        Node* prev;
        Node* next;

        Node(int k, int v) : key(k), value(v), prev(nullptr), next(nullptr) {}
    };

public:
    explicit LRUCache(int capacity) : capacity_(capacity) {
        head_ = new Node(0, 0);
        tail_ = new Node(0, 0);
        head_->next = tail_;
        tail_->prev = head_;
    }

    ~LRUCache() {
        Node* cur = head_;
        while (cur != nullptr) {
            Node* next = cur->next;
            delete cur;
            cur = next;
        }
    }

    int get(int key) {
        auto it = table_.find(key);
        if (it == table_.end()) {
            return -1;
        }

        moveToFront(it->second);
        return it->second->value;
    }

    void put(int key, int value) {
        auto it = table_.find(key);
        if (it != table_.end()) {
            it->second->value = value;
            moveToFront(it->second);
            return;
        }

        Node* node = new Node(key, value);
        table_[key] = node;
        addToFront(node);

        if (static_cast<int>(table_.size()) > capacity_) {
            Node* victim = tail_->prev;
            removeNode(victim);
            table_.erase(victim->key);
            delete victim;
        }
    }

private:
    void addToFront(Node* node) {
        node->next = head_->next;
        node->prev = head_;
        head_->next->prev = node;
        head_->next = node;
    }

    void removeNode(Node* node) {
        node->prev->next = node->next;
        node->next->prev = node->prev;
    }

    void moveToFront(Node* node) {
        removeNode(node);
        addToFront(node);
    }

    int capacity_;
    std::unordered_map<int, Node*> table_;
    Node* head_;
    Node* tail_;
};
```

### 常见追问

- 如何改成模板版本
- 如何做到线程安全
- 如何避免手写裸指针

### 补充理解

- LRU 的关键不是代码量，而是“哈希表负责定位，双向链表负责维护访问顺序”
- `get` 和 `put` 都要求平均 O(1)，因此不能用普通数组或只用链表
- 手写版本常见 bug 是忘记维护前后指针、忘记同步更新哈希表、析构时漏释放节点

---

## 7. 用两个栈实现队列

### 题目描述

使用两个栈实现先进先出的队列。


### English explanation

In an English interview, I would say:

Use two stacks to implement a first-in-first-out queue.

### 面试官常看点

- 是否理解摊还复杂度
- 是否能把 `inStack` 和 `outStack` 的职责讲清楚

### 标准思路

- 入队时压入 `inStack`
- 出队时若 `outStack` 为空，则把 `inStack` 所有元素倒过去

### 代码实现

```cpp
#include <stack>
#include <stdexcept>

class MyQueue {
public:
    void push(int x) {
        in_.push(x);
    }

    int pop() {
        moveIfNeeded();
        if (out_.empty()) {
            throw std::runtime_error("queue is empty");
        }
        int value = out_.top();
        out_.pop();
        return value;
    }

    int front() {
        moveIfNeeded();
        if (out_.empty()) {
            throw std::runtime_error("queue is empty");
        }
        return out_.top();
    }

private:
    void moveIfNeeded() {
        if (!out_.empty()) {
            return;
        }

        while (!in_.empty()) {
            out_.push(in_.top());
            in_.pop();
        }
    }

    std::stack<int> in_;
    std::stack<int> out_;
};
```

### 常见追问

- 用两个队列实现栈怎么做
- 为什么是摊还 O(1)

### 补充理解

- 单次 `pop` 可能触发一批元素搬运，但每个元素只会被搬过去一次，所以摊还仍是 O(1)
- 这题考的是“用已有数据结构模拟另一种语义”
- 面试里最好主动说明空队列时如何处理异常或错误码

---

## 8. 实现最小栈

### 题目描述

设计一个栈，支持 `push`、`pop`、`top` 和 `getMin`，都要求 O(1)。


### English explanation

In an English interview, I would say:

Design a stack that supports `push`, `pop`, `top` and `getMin`, all requiring O(1).

### 面试官常看点

- 是否能想到辅助栈
- 是否正确处理重复最小值

### 标准思路

维护两个栈：

- 一个正常存值
- 一个同步维护当前最小值

### 代码实现

```cpp
#include <stack>
#include <stdexcept>

class MinStack {
public:
    void push(int val) {
        data_.push(val);
        if (mins_.empty() || val <= mins_.top()) {
            mins_.push(val);
        }
    }

    void pop() {
        if (data_.empty()) {
            throw std::runtime_error("stack is empty");
        }
        if (data_.top() == mins_.top()) {
            mins_.pop();
        }
        data_.pop();
    }

    int top() const {
        if (data_.empty()) {
            throw std::runtime_error("stack is empty");
        }
        return data_.top();
    }

    int getMin() const {
        if (mins_.empty()) {
            throw std::runtime_error("stack is empty");
        }
        return mins_.top();
    }

private:
    std::stack<int> data_;
    std::stack<int> mins_;
};
```

### 常见追问

- 能否只用一个栈实现
- 如果元素类型不是整数怎么办

### 补充理解

- 最小栈核心是“在普通栈旁边维护一份最小值轨迹”
- 处理重复最小值时要特别小心，常见做法是相等时也压入辅助栈
- 这题考的是空间换时间思维

---

## 9. 手写线程安全队列

### 题目描述

设计一个多线程可用的队列，支持生产者和消费者并发访问。


### English explanation

In an English interview, I would say:

Design a multi-threaded queue to support concurrent access by producers and consumers.

### 面试官常看点

- 是否知道 `mutex + condition_variable`
- 是否处理空队列等待
- 是否理解伪唤醒

### 标准思路

- 入队时加锁并通知一个等待线程
- 出队时若队列为空则等待条件变量
- 等待条件必须用谓词循环检查

### 代码实现

```cpp
#include <condition_variable>
#include <mutex>
#include <queue>

template <typename T>
class ThreadSafeQueue {
public:
    void push(T value) {
        {
            std::lock_guard<std::mutex> lock(mtx_);
            queue_.push(std::move(value));
        }
        cv_.notify_one();
    }

    T waitAndPop() {
        std::unique_lock<std::mutex> lock(mtx_);
        cv_.wait(lock, [this] { return !queue_.empty(); });

        T value = std::move(queue_.front());
        queue_.pop();
        return value;
    }

    bool tryPop(T& value) {
        std::lock_guard<std::mutex> lock(mtx_);
        if (queue_.empty()) {
            return false;
        }
        value = std::move(queue_.front());
        queue_.pop();
        return true;
    }

private:
    std::mutex mtx_;
    std::condition_variable cv_;
    std::queue<T> queue_;
};
```

### 常见追问

- 如何支持关闭队列
- 如何避免返回值拷贝
- 能否做成无锁队列

### 补充理解

- `condition_variable` 等待时必须配合谓词或循环，避免伪唤醒问题
- `push` 通常在释放锁后再通知，减少不必要竞争
- 这类题目里，先写出正确阻塞队列，再讨论 lock-free，层次会更好

---

## 10. 实现线程池时，任务队列需要考虑什么？

### 题目描述

如果让你实现一个简单线程池，你会怎么设计任务队列？


### English explanation

In an English interview, I would say:

If you were asked to implement a simple thread pool, how would you design the task queue?

### 面试官常看点

- 是否理解生产者消费者模型
- 是否考虑 stop 标志和优雅退出
- 是否知道任务要支持可调用对象

### 标准思路

- 队列存 `std::function<void()>`
- 工作线程循环等待任务
- 线程池析构时设置停止标记并唤醒所有线程

### 代码片段

```cpp
#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>

class TaskQueue {
public:
    void push(std::function<void()> task) {
        {
            std::lock_guard<std::mutex> lock(mtx_);
            tasks_.push(std::move(task));
        }
        cv_.notify_one();
    }

    bool waitAndPop(std::function<void()>& task) {
        std::unique_lock<std::mutex> lock(mtx_);
        cv_.wait(lock, [this] { return stopped_ || !tasks_.empty(); });

        if (stopped_ && tasks_.empty()) {
            return false;
        }

        task = std::move(tasks_.front());
        tasks_.pop();
        return true;
    }

    void stop() {
        {
            std::lock_guard<std::mutex> lock(mtx_);
            stopped_ = true;
        }
        cv_.notify_all();
    }

private:
    std::mutex mtx_;
    std::condition_variable cv_;
    std::queue<std::function<void()>> tasks_;
    bool stopped_ = false;
};
```

### 常见追问

- 如何支持返回值和 future
- 如何限制任务队列长度
- 如何处理异常任务

### 补充理解

- 线程池本质是“任务队列 + 工作线程 + 停止协议”
- 真正工程实现里，停止逻辑、异常传播和任务返回值往往比“启动几个线程”更关键
- 如果面试官继续追问，可以延伸到 `packaged_task`、`future`、背压和优雅关闭

---

## 手写题复习建议

- 链表题练到不画图也能写出来
- LRU 要能口述“哈希表 + 双向链表”的原因
- 并发题先保证正确，再谈性能
- 每道题都要能说出时间复杂度和空间复杂度
