# STL 容器速查表

这份文档不按难度分级，而按“选容器时你真正关心的问题”来整理：

- 底层结构
- 时间复杂度
- 内存布局
- 迭代器失效
- 适用场景
- 高频面试追问

---

## 1. 先记住一条默认原则

如果没有明确理由，默认优先考虑：

- 顺序容器：`std::vector`
- 键值查找：`std::unordered_map`
- 去重集合：`std::unordered_set`

然后再根据下面这些问题修正选择：

- 是否需要有序遍历
- 是否需要随机访问
- 是否需要头部插入删除
- 是否非常在意缓存友好
- 是否需要稳定的迭代器、引用、指针

### 错误回答示例

- “容器选型只看复杂度表就够了”
- “默认就该用链表，因为插入删除快”
- “所有场景统一 `vector` 或统一 `unordered_map` 就行”


### English explanation

In an English interview, I would say:

- "When selecting a container, just look at the complexity table."
- "By default, linked lists should be used because insertion and deletion are fast"
- "Just unify `vector` or unify `unordered_map` for all scenes"

### 面试官想听什么

- 你是否知道容器选择是“访问模式 + 内存布局 + 语义”共同决定的
- 你是否知道默认选择可以有，但必须知道何时修正

### 项目里怎么说

我会先从默认容器开始建模，再根据是否需要顺序、随机访问、双端操作、稳定迭代器这些约束修正，而不是上来就背复杂度表选容器。

---

## 2. 顺序容器总览

| 容器 | 底层结构 | 是否连续内存 | 随机访问 | 头部插删 | 中间插删 | 尾部插入 | 典型场景 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `vector` | 动态数组 | 是 | 快 | 慢 | 慢 | 快，摊还 O(1) | 默认顺序容器 |
| `array` | 固定长度数组封装 | 是 | 快 | 不适用 | 不适用 | 不适用 | 固定大小数据 |
| `deque` | 分段连续存储 | 不是整体连续 | 快 | 快 | 一般 | 快 | 双端操作频繁 |
| `list` | 双向链表 | 否 | 不支持 | 快 | 快 | 快 | 已知位置频繁插删 |
| `forward_list` | 单向链表 | 否 | 不支持 | 头部快 | 一般 | 不适合 | 极简单链表场景 |

---

## 3. `vector`

### 关键特性

- 默认顺序容器
- 连续内存，缓存友好
- 支持随机访问
- 尾部插入效率高


### English explanation

In an English interview, I would say:

- Default order container
- Contiguous memory, cache friendly
- Support random access
- High tail insertion efficiency

### 时间复杂度

- `operator[]` / `at()`：O(1)
- `push_back()`：摊还 O(1)
- 尾部删除：O(1)
- 中间插入/删除：O(n)
- 查找：O(n)

### 内存布局

- `vector` 对象本身通常可以在栈上
- 元素通常在堆上动态分配
- 扩容时可能重新申请更大内存，并整体搬迁旧元素

### 迭代器失效

- 扩容后，原有迭代器、引用、指针通常全部失效
- 中间插入/删除后，插入点及其后的迭代器可能失效

### 高频面试追问

- `reserve()` 和 `resize()` 的区别
- 为什么 `vector` 常常比 `list` 更快
- 扩容策略大概是什么

### 什么时候用

- 几乎所有默认顺序存储场景
- 需要随机访问
- 需要和 STL 算法紧密配合

### 什么时候别急着用

- 频繁头插头删
- 非常依赖稳定引用/迭代器

### 错误回答示例

- “`vector` 所有操作都最快”
- “扩容只是性能问题，不影响正确性”
- “只要用 STL，默认都该换成 `list`”

### 面试官想听什么

- 你是否知道 `vector` 的优势来自连续内存和缓存友好
- 你是否知道它的主要风险点是扩容和迭代器失效

### 项目里怎么说

我会把 `vector` 当作默认顺序容器，因为它和算法协作最好、缓存友好、随机访问快。只有在访问模式明显不适合时才切换其他容器。

---

## 4. `array`

### 关键特性

- 固定长度
- 连续内存
- 大小是类型的一部分


### English explanation

In an English interview, I would say:

- fixed length
- contiguous memory
- size is part of type

### 时间复杂度

- 随机访问：O(1)
- 没有动态扩容

### 内存布局

- `std::array<T, N>` 本质上像“带接口的固定数组”
- 它放在哪里取决于它作为哪个对象的一部分
- 局部变量形式时，整体通常在栈上

### 迭代器失效

- 不存在扩容问题
- 只要对象本身还活着，迭代器通常稳定

### 什么时候用

- 大小固定
- 想表达“固定长度语义”
- 希望兼顾数组性能和 STL 接口

### 错误回答示例

- “`array` 一定在栈上，所以一定更好”
- “固定大小就没必要用 STL 容器”
- “`array` 和 C 风格数组完全没有区别”

### 面试官想听什么

- 你是否知道 `array` 的大小是类型的一部分
- 你是否知道它保留了数组性能，同时提供 STL 风格接口

### 项目里怎么说

如果长度固定且我希望类型系统直接表达这个约束，我会优先 `std::array`，这样比裸数组更安全，也更容易和 STL 算法配合。

---

## 5. `deque`

### 关键特性

- 双端队列
- 支持头尾快速插删
- 支持随机访问
- 不是整体连续内存


### English explanation

In an English interview, I would say:

- Deque
- Supports quick insertion and deletion of head and tail
- Support random access
- Not overall contiguous memory

### 时间复杂度

- 头尾插删：通常 O(1)
- 随机访问：O(1)
- 中间插删：一般较慢

### 内存布局

- 通常是分段连续存储
- 比 `vector` 更灵活，但缓存友好性通常略差

### 迭代器失效

- 比 `vector` 规则更复杂
- 插入删除两端元素时，部分实现中迭代器可能失效
- 面试里通常答到“比 `vector` 更复杂，需要查具体规则”即可

### 什么时候用

- 频繁头尾操作
- 需要比 `list` 更好的随机访问能力

### 错误回答示例

- “`deque` 就是双向链表”
- “它和 `vector` 唯一差别就是能头插”
- “只要有双端操作需求就一定应该用 `deque`”

### 面试官想听什么

- 你是否知道 `deque` 支持随机访问，但不是整体连续内存
- 你是否知道它是在 `vector` 和 `list` 之间做权衡

### 项目里怎么说

如果我需要双端操作但又不想退化到链表，我会考虑 `deque`。但如果主要还是顺序遍历和算法处理，我通常仍会优先 `vector`。

---

## 6. `list`

### 关键特性

- 双向链表
- 节点分散存储
- 不支持随机访问
- 迭代器通常更稳定


### English explanation

In an English interview, I would say:

- Doubly linked list
- Node decentralized storage
- Random access is not supported
- Iterators are generally more stable

### 时间复杂度

- 已知位置插入/删除：O(1)
- 查找某个位置：O(n)
- 随机访问：不支持

### 内存布局

- 每个节点单独分配
- 节点之间通过指针链接
- 额外指针开销明显

### 迭代器失效

- 插入删除其他节点时，未被删除节点的迭代器通常仍然有效
- 被删除节点对应的迭代器失效

### 高频面试追问

- 为什么理论上插入快，但工程里很多时候不如 `vector`
- `splice()` 有什么价值

### 什么时候用

- 已经持有目标位置迭代器
- 中间插删极多
- 强依赖稳定节点/稳定迭代器

### 什么时候别优先用

- 大量顺序遍历但更看重 cache
- 需要随机访问

### 错误回答示例

- “链表插删是 O(1)，所以默认更高效”
- “`list` 适合一切经常修改的场景”
- “有了 `list` 就不需要考虑迭代器失效”

### 面试官想听什么

- 你是否知道 `list` 的理论复杂度优势并不自动转化为真实工程优势
- 你是否知道它真正适用的前提往往是“已持有目标位置迭代器”

### 项目里怎么说

我只有在确实需要稳定节点、频繁中间插删、并且通常已经有目标位置迭代器时，才会认真考虑 `list`。否则默认仍会优先 `vector`。

---

## 7. `map` vs `unordered_map`

| 容器 | 底层 | 顺序 | 平均查找 | 最坏查找 | 范围查询 | 典型用途 |
| --- | --- | --- | --- | --- | --- | --- |
| `map` | 平衡树 | 有序 | O(log n) | O(log n) | 支持 | 有序键值表 |
| `unordered_map` | 哈希表 | 无序 | O(1) | O(n) | 不适合 | 高频 key lookup |

### `map` 重点

- 键有序
- 支持 `lower_bound`、`upper_bound`
- 适合范围查询、有序输出


### English explanation

In an English interview, I would say:

- Keys ordered
- Support `lower_bound`, `upper_bound`
- Suitable for range query and ordered output

### `unordered_map` 重点

- 平均查找更快
- 不保证顺序
- 性能受哈希函数和冲突影响

### 选型建议

- 需要顺序、范围查询、稳定输出：`map`
- 只关心查找效率：`unordered_map`

### 错误回答示例

- “`unordered_map` 一定比 `map` 快”
- “`map` 已经过时”
- “选这个只要看平均复杂度”

### 面试官想听什么

- 你是否知道一个强调顺序和范围查询，一个强调平均查找效率
- 你是否知道最坏复杂度、哈希冲突和调试体验也要考虑

### 项目里怎么说

如果业务逻辑依赖键顺序、范围查询或稳定输出，我会选 `map`；如果主要是高频 key lookup 且不依赖顺序，我会优先考虑 `unordered_map`。

---

## 8. `set` vs `unordered_set`

| 容器 | 是否有序 | 是否重复 | 平均查找 | 典型用途 |
| --- | --- | --- | --- | --- |
| `set` | 有序 | 不允许 | O(log n) | 有序去重集合 |
| `unordered_set` | 无序 | 不允许 | O(1) | 快速 membership test |

### 核心理解

- 它们表达的是“集合语义”，不是“少功能版容器”
- 重点不在于存值，而在于“元素唯一”


### English explanation

In an English interview, I would say:

- They express "collection semantics", not "less functional containers"
- The focus is not on stored value, but on "uniqueness of elements"

### 错误回答示例

- “`set` 就是不能重复的 `vector`”
- “只要元素唯一就随便选”
- “`unordered_set` 一定更好”

### 面试官想听什么

- 你是否知道集合容器关注的是去重语义
- 你是否能根据顺序需求和查找需求做选择

### 项目里怎么说

如果我需要去重并保持有序遍历，会选 `set`；如果只关心元素是否存在且不关心顺序，会优先考虑 `unordered_set`。

---

## 9. 适配器：`stack`、`queue`、`priority_queue`

### `stack`

- 语义：后进先出
- 常用接口：`push`、`pop`、`top`
- 常见场景：表达式求值、括号匹配、DFS 辅助


### English explanation

In an English interview, I would say:

- Semantics: last in, first out
- Common interfaces: `push`, `pop`, `top`
- Common scenarios: expression evaluation, bracket matching, DFS assistance

### `queue`

- 语义：先进先出
- 常用接口：`push`、`pop`、`front`
- 常见场景：BFS、任务调度

### `priority_queue`

- 语义：优先级最高元素先出
- 默认：最大堆
- 常见场景：Top K、调度、贪心

### 关键提醒

- 它们是容器适配器，不是底层存储结构本身
- `queue` / `stack` 默认常常基于 `deque`

### 错误回答示例

- “它们就是普通容器”
- “`priority_queue` 会自动给你排成一个有序数组”
- “`queue` 就等于 `deque`”

### 面试官想听什么

- 你是否知道它们提供的是受限接口
- 你是否知道 `priority_queue` 的核心是堆语义，不是完整排序结果

### 项目里怎么说

如果业务只需要队列、栈或堆顶优先访问语义，我会直接使用适配器，而不是用底层容器自己手工约束接口。

---

## 10. 迭代器失效速查

### `vector`

- 扩容：基本全失效
- 中间插删：该点及之后可能失效


### English explanation

In an English interview, I would say:

- Expansion: Basically all failures
- Intermediate insertion and deletion: this point and later may be invalid.

### `deque`

- 规则较复杂
- 两端插删和中间插删都可能导致部分失效

### `list`

- 删除节点本身失效
- 其他节点迭代器通常稳定

### `map` / `set`

- 插入通常不让已有迭代器失效
- 删除某个元素只让该元素迭代器失效

### 面试回答建议

如果记不住全部细节，至少要稳稳说出：

- `vector` 扩容是高频失效点
- `list` 迭代器更稳定
- 关联容器通常比 `vector` 稳定

### 错误回答示例

- “迭代器拿到之后就一直能用”
- “只有删除元素才会失效”
- “所有容器的失效规则差不多”

### 面试官想听什么

- 你是否知道容器修改可能破坏旧迭代器、引用和指针
- 你是否能说出 `vector` 扩容这一最常见风险点

### 项目里怎么说

我在写 STL 代码时会特别小心容器修改后的旧迭代器复用问题，尤其是 `vector` 的插入、扩容和 erase 之后的代码路径。

---

## 11. 容器选型速记

### 如果你只记一句话

- 默认顺序容器：`vector`
- 默认哈希查找：`unordered_map`
- 默认去重集合：`unordered_set`


### English explanation

In an English interview, I would say:

- Default order container: `vector`
- Default hash lookup: `unordered_map`
- Default deduplication set: `unordered_set`

### 如果你还记两句

- 需要有序：`map` / `set`
- 需要头尾操作：`deque`

### 如果你再记一句

- 非常依赖中间插删且已有位置迭代器：才认真考虑 `list`

### 错误回答示例

- “我习惯哪个就一直用哪个”
- “面试只要背出复杂度就够了”
- “先选容器，再想访问模式”

### 面试官想听什么

- 你是否能用一句清楚的话讲出默认选择和修正原则
- 你是否能把选型结论落到真实访问模式上

### 项目里怎么说

我通常先用默认容器快速建模，再根据访问模式、顺序需求、稳定性要求和性能瓶颈做针对性替换。

---

## 12. 高频面试问法

### 为什么 `vector` 经常比 `list` 快？

因为 `vector` 连续内存、缓存友好；`list` 虽然理论上插删复杂度好，但节点分散、指针跳转多，真实 CPU 行为往往更差。


### English explanation

In an English interview, I would say:

Because `vector` has continuous memory and is cache-friendly; although `list` has good insertion and deletion complexity in theory, it has scattered nodes and many pointer jumps, and the real CPU behavior is often worse.

### `reserve()` 和 `resize()` 的区别？

- `reserve()` 改容量，不改逻辑大小
- `resize()` 改逻辑大小，可能创建新元素

### 为什么 `unordered_map` 不是一定比 `map` 好？

因为它不保序、最坏复杂度可能变差，而且哈希表有冲突和内存开销问题。

### 为什么 `list` 不支持 `operator[]`？

因为链表不支持常数时间随机访问。

---

## 13. 复习建议

- 背复杂度之前，先理解底层结构
- 背迭代器失效之前，先理解容器是否会搬家
- 背选型结论之前，先问自己访问模式是什么
