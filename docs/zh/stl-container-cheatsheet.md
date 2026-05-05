# STL 容器速查表

这份文档按 flashcard 结构整理 STL 容器。重点不是只背复杂度表，而是把访问模式、内存布局、迭代器失效和项目选型联系起来。

## 1. 先记住一条默认原则

### 核心答案

没有明确理由时，顺序容器先考虑 `vector`，键值查找先考虑 `unordered_map`，去重集合先考虑 `unordered_set`，再根据顺序、随机访问、插删位置、迭代器稳定性修正。

### English explanation

In an English interview, I would answer it like this:

Default to `vector`, `unordered_map`, and `unordered_set`, then adjust based on ordering, access pattern, insertion pattern, and iterator stability.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <string>
#include <unordered_map>
#include <vector>

std::vector<int> samples;
std::unordered_map<std::string, int> counts;
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 2. 顺序容器总览

### 核心答案

顺序容器的核心差异是内存是否连续、是否支持随机访问、在哪个位置插删快，以及迭代器失效规则。

### English explanation

In an English interview, I would answer it like this:

Sequence containers mainly differ in memory layout, random access, insertion position, and iterator invalidation.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <array>
#include <deque>
#include <list>
#include <vector>

std::vector<int> a;
std::array<int, 4> b{};
std::deque<int> c;
std::list<int> d;
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 3. `vector`

### 核心答案

`vector` 是默认顺序容器：连续内存、随机访问快、尾插摊还 O(1)，但扩容会导致迭代器、引用、指针失效。

### English explanation

In an English interview, I would answer it like this:

`vector` is the default sequence container: contiguous storage, fast random access, amortized O(1) push_back, but reallocation invalidates iterators and references.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <vector>

int main() {
    std::vector<int> v;
    v.reserve(100);
    v.push_back(1);
    int x = v[0];
    (void)x;
}
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 4. `array`

### 核心答案

`std::array<T,N>` 是固定大小数组封装，大小是类型的一部分，连续内存、无动态分配，适合编译期已知长度的小数组。

### English explanation

In an English interview, I would answer it like this:

`std::array` wraps a fixed-size contiguous array with value semantics and no dynamic allocation.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <array>

std::array<int, 3> rgb{255, 128, 0};
static_assert(rgb.size() == 3);
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 5. `deque`

### 核心答案

`deque` 支持头尾高效插删和随机访问，但不是整体连续内存；适合队列式双端增长，不适合要求连续 buffer 的接口。

### English explanation

In an English interview, I would answer it like this:

`deque` supports efficient insertion at both ends and random access, but its storage is not one contiguous block.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <deque>

int main() {
    std::deque<int> q;
    q.push_front(1);
    q.push_back(2);
    int first = q.front();
    (void)first;
}
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 6. `list`

### 核心答案

`list` 是双向链表，已知位置插删稳定，但随机访问差、缓存不友好；现代 C++ 中不应因为“插删 O(1)”就默认选择它。

### English explanation

In an English interview, I would answer it like this:

`list` has stable node insertion and removal at known positions, but poor cache locality and no random access.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <list>

int main() {
    std::list<int> xs{1, 3};
    auto it = xs.begin();
    ++it;
    xs.insert(it, 2);
}
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 7. `map` vs `unordered_map`

### 核心答案

`map` 有序、迭代顺序稳定、基于比较；`unordered_map` 平均查找快、基于哈希、无序但受哈希质量和 rehash 影响。

### English explanation

In an English interview, I would answer it like this:

`map` is ordered and comparison-based; `unordered_map` is hash-based, usually faster on average, but unordered and affected by hashing and rehashing.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <map>
#include <string>
#include <unordered_map>

std::map<std::string, int> ordered;
std::unordered_map<std::string, int> fast_lookup;
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 8. `set` vs `unordered_set`

### 核心答案

`set` 维护有序唯一集合，适合有序遍历和范围查询；`unordered_set` 适合平均 O(1) 去重查找，但不保证顺序。

### English explanation

In an English interview, I would answer it like this:

`set` keeps ordered unique values; `unordered_set` provides hash-based uniqueness without ordering.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <set>
#include <unordered_set>

std::set<int> sorted_ids;
std::unordered_set<int> seen_ids;
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 9. 适配器：`stack`、`queue`、`priority_queue`

### 核心答案

容器适配器限制接口来表达特定访问模式：`stack` 后进先出，`queue` 先进先出，`priority_queue` 每次取优先级最高元素。

### English explanation

In an English interview, I would answer it like this:

Container adaptors restrict operations to express stack, queue, and priority-queue access patterns.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <queue>
#include <stack>

std::stack<int> st;
std::queue<int> q;
std::priority_queue<int> pq;
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 10. 迭代器失效速查

### 核心答案

迭代器失效是 STL 高频坑：`vector` 扩容通常全失效，`unordered_map` rehash 迭代器失效，链表插删通常只影响被删节点。

### English explanation

In an English interview, I would answer it like this:

Iterator invalidation is a common STL pitfall: vector reallocation invalidates broadly, unordered_map rehash invalidates iterators, and list is more stable.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <vector>

int main() {
    std::vector<int> v{1, 2};
    auto it = v.begin();
    v.push_back(3); // 可能扩容，it 可能失效
}
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 11. 容器选型速记

### 核心答案

容器选型先看访问模式：遍历和随机访问选 `vector`，有序选 `map/set`，哈希查找选 `unordered_*`，双端选 `deque`，已知位置稳定插删才考虑 `list`。

### English explanation

In an English interview, I would answer it like this:

Choose containers by access pattern: vector for traversal/random access, map/set for ordering, unordered containers for hash lookup, deque for both ends, list for stable known-position edits.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <deque>
#include <map>
#include <unordered_map>
#include <vector>

// 选型不是背名字，而是匹配访问模式。
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 12. 高频面试问法

### 核心答案

常见追问集中在 `vector` 为什么常比 `list` 快、`reserve` vs `resize`、`unordered_map` 为什么不一定比 `map` 好、迭代器何时失效。

### English explanation

In an English interview, I would answer it like this:

Common interview follow-ups focus on vector vs list, reserve vs resize, unordered_map tradeoffs, and iterator invalidation.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <vector>

int main() {
    std::vector<int> v;
    v.reserve(10); // 改 capacity，不改 size
    v.resize(5);   // 改 size，构造元素
}
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---

## 13. 复习建议

### 核心答案

STL 容器复习不要只背复杂度表，要把复杂度、内存布局、缓存友好、迭代器失效和工程语义一起说清。

### English explanation

In an English interview, I would answer it like this:

When reviewing STL containers, combine complexity, memory layout, cache locality, iterator invalidation, and semantic intent.

### 错误回答示例

- “容器选型只看复杂度表”
- “链表插删 O(1)，所以默认比 vector 好”
- “unordered 容器一定比有序容器快”

### 面试官想听什么

- 你是否能结合访问模式和内存布局选容器
- 你是否知道迭代器、引用、指针什么时候会失效
- 你是否能说清默认选择以及修正条件

### 项目里怎么说

项目里我会先从默认容器开始，再按约束修正：是否需要有序、随机访问、双端操作、稳定迭代器、连续内存或哈希查找。选型要服务于数据访问模式，而不是服务于背复杂度表。

### 深入解释

- 连续内存通常更缓存友好，遍历性能常常优于节点式容器
- 哈希容器平均查找快，但受哈希质量、负载因子和 rehash 影响
- 有序容器提供排序和范围查询，这是 unordered 容器没有的语义
- 迭代器失效经常比单次操作复杂度更容易导致真实 bug

### 示例

```cpp
#include <vector>

// 默认 vector，然后按约束修正。
std::vector<int> default_sequence;
```

### 代码讲解

- 示例展示该容器或选型原则的最小用法
- 面试时要补充它的访问模式、内存布局和失效规则
- 如果保存了迭代器、引用或指针，要说明后续插入删除是否安全
- 项目选型里要解释为什么不用另一个常见容器

### 高频坑

- 不要只说“快”，要说是哪种操作快
- 不要忽略扩容、rehash 和迭代器失效
- 不要把底层结构当成唯一依据，接口语义同样重要

---
