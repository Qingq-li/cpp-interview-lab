# C++ 面试笔记：高级篇

这一篇对应深入追问和区分度问题。回答重点不只是“是什么”，而是“为什么这样设计、这样设计的代价是什么、工程里如何取舍”。

---

## 1. 什么是完美转发？

### 核心答案

完美转发是指模板包装层在转发参数时，尽量保留参数原本的左值或右值属性。


### English explanation

In an English interview, I would say:

Perfect forwarding means that when forwarding parameters, the template packaging layer tries to retain the original lvalue or rvalue attributes of the parameters.

### 错误回答示例

- “完美转发就是把参数都 `std::move` 一下”
- “有了右值引用就自动是完美转发”
- “模板里 `T&&` 永远都是右值引用”

### 面试官想听什么

- 你是否知道完美转发依赖转发引用和 `std::forward`
- 你是否理解它解决的是包装层丢失值类别的问题

### 项目里怎么说

我会在工厂函数、通用包装器和模板容器接口里使用完美转发，避免中间层把调用方传入的左值/右值属性破坏掉。

### 深入解释

- 完美转发的关键不是 `T&&` 三个字符，而是“推导 + `std::forward` + 保持值类别”
- 如果包装层总把参数当左值传下去，会错过移动语义；如果总 `std::move`，又可能把调用方左值错误搬走
- 这类机制在 `emplace`、工厂函数和泛型封装中非常常见
- 完美转发本质上是为了让中间层“不篡改调用语义”

### 示例

```cpp
#include <iostream>
#include <utility>

void process(int& x) {
    std::cout << "lvalue: " << x << '\n';
}

void process(int&& x) {
    std::cout << "rvalue: " << x << '\n';
}

template <typename T>
void wrapper(T&& value) {
    process(std::forward<T>(value));
}

int main() {
    int x = 10;
    wrapper(x);
    wrapper(20);
}
```

### 代码讲解

- `template <typename T> void wrapper(T&& value)` 这里的 `T&&` 是转发引用
- `wrapper(x);` 传入左值 `x`
- `wrapper(20);` 传入右值临时量
- `std::forward<T>(value)` 是关键，它会保留调用方原本的值类别
- 这段代码重点看：同一个包装函数既能正确转发左值，也能正确转发右值

---

## 2. `std::move` 和 `std::forward` 的区别是什么？

### 核心答案

- `std::move` 无条件把表达式转成右值语义
- `std::forward` 在模板上下文中按原始值类别转发


### English explanation

In an English interview, I would say:

- `std::move` unconditionally converts expressions to rvalue semantics
- `std::forward` forward by primitive value category in template context

### 错误回答示例

- “两者只是名字不同”
- “`forward` 比 `move` 更快”
- “只要想优化性能就加 `move`”

### 面试官想听什么

- 你是否知道 `move` 是显式声明“这个对象可以被搬走”
- 你是否知道 `forward` 的存在是为了模板保真转发

### 项目里怎么说

非模板代码里我基本只会在明确不再使用对象时调用 `std::move`；模板包装层则会谨慎使用 `std::forward`，避免错误地把左值也当成右值转走。

### 深入解释

- `std::move` 更像一个类型转换工具，而不是执行移动的函数
- 真正是否发生移动，要看后续是否匹配到移动构造、移动赋值或右值重载
- `std::forward` 只有在模板参数推导场景下才真正体现价值
- 很多面试官问这一题，是为了看你是否理解值类别传播，而不是背两个 API 定义

---

## 3. 什么是 SFINAE？

### 核心答案

SFINAE 的意思是模板替换失败不是错误，而是让不合法候选退出重载决议。


### English explanation

In an English interview, I would say:

SFINAE means that failure of template replacement is not an error, but causes illegal candidates to exit overload resolution.

### 错误回答示例

- “SFINAE 就是模板编译报错技巧”
- “它和概念完全一样”
- “现代 C++ 里已经没用了”

### 面试官想听什么

- 你是否知道它是旧式模板约束的核心机制
- 你是否能把它和 `enable_if`、traits、重载控制联系起来

### 项目里怎么说

老代码和基础库中仍会遇到 SFINAE。新代码如果编译器和标准允许，我会更倾向 `if constexpr`、`requires` 和 `concepts`，因为可读性更强。

### 深入解释

- SFINAE 的价值在于“非法模板候选自动退出”，而不是把程序直接编译报死
- 它让模板可以根据类型特征有选择地参与重载
- 历史上大量模板库都依赖 SFINAE，因此理解它对读旧代码很重要
- 现代语言特性在逐步替代它的部分用途，但底层思想仍然一致：对模板施加约束

### 示例

```cpp
#include <iostream>
#include <type_traits>

template <typename T>
typename std::enable_if<std::is_integral<T>::value, void>::type
printType(T) {
    std::cout << "integral\n";
}

template <typename T>
typename std::enable_if<!std::is_integral<T>::value, void>::type
printType(T) {
    std::cout << "non-integral\n";
}
```

### 代码讲解

- `std::enable_if<...>::type` 用来控制这个函数模板是否有效
- 第一组模板只允许整数类型参与重载
- 第二组模板只允许非整数类型参与重载
- 这段代码重点看：不满足条件的模板不会硬报错，而是自动退出候选集合

---

## 4. 静态多态和动态多态有什么区别？

### 核心答案

- 动态多态基于虚函数，运行时分发
- 静态多态基于模板或 CRTP，编译期分发


### English explanation

In an English interview, I would say:

- Dynamic polymorphism is based on virtual functions and distributed at runtime
- Static polymorphism based on templates or CRTP, distributed at compile time

### 错误回答示例

- “模板不是多态”
- “动态多态一定更慢所以不用”
- “静态多态能完全替代虚函数”

### 面试官想听什么

- 你是否能根据扩展时机和性能需求选择方案
- 你是否知道运行时扩展和编译期优化是两条不同维度

### 项目里怎么说

如果需要插件式扩展、运行时切换实现，我会优先动态多态；如果能力边界在编译期已知，而且性能敏感，我会更考虑模板和静态多态。

### 深入解释

- 动态多态适合“运行时才知道具体类型”的场景，比如插件系统、策略替换、接口注入
- 静态多态更适合编译期已知类型的高性能抽象，比如数值计算和泛型库
- 动态多态通常伴随虚表和间接调用，静态多态则可能带来代码膨胀
- 工程选择往往不是“谁高级”，而是“扩展时机和性能边界是否匹配”

### 示例

```cpp
#include <iostream>

template <typename T>
class Printer {
public:
    void print() const {
        static_cast<const T*>(this)->printImpl();
    }
};

class MessagePrinter : public Printer<MessagePrinter> {
public:
    void printImpl() const {
        std::cout << "hello\n";
    }
};
```

### 代码讲解

- `Printer<T>` 是基类模板，`T` 表示最终派生类型
- `static_cast<const T*>(this)->printImpl();` 是 CRTP 的核心写法
- 它把接口调用下沉到派生类实现，但在编译期就能确定目标
- 这段代码重点看：没有虚函数，也能实现“统一接口 + 不同实现”

---

## 5. 什么是对象切片？

### 核心答案

派生类对象按值传给基类对象时，只会保留基类部分，派生类部分被切掉，这就是对象切片。


### English explanation

In an English interview, I would say:

When a derived class object is passed to a base class object by value, only the base class part will be retained, and the derived class part will be cut off. This is object slicing.

### 错误回答示例

- “有虚函数就不会切片”
- “切片只是少调一个析构函数”
- “只有显式拷贝才会切片”

### 面试官想听什么

- 你是否知道按值传基类会破坏多态
- 你是否知道多态接口应该用基类引用或指针

### 项目里怎么说

如果接口语义上允许多态，我会显式禁止按值接收基类对象，统一用引用、指针或智能指针，避免切片把真实动态类型信息丢掉。

### 深入解释

- 对象切片本质上是“派生对象被按值转换成基类对象时，只复制基类子对象”
- 一旦切片发生，派生类新增状态和行为信息就丢失了
- 即使基类有虚函数，切成一个独立的基类对象后，多态也无法恢复
- 因此多态接口设计通常都避免按值传递基类

### 示例

```cpp
#include <iostream>

class Base {
public:
    virtual void who() const {
        std::cout << "Base\n";
    }
};

class Derived : public Base {
public:
    void who() const override {
        std::cout << "Derived\n";
    }
};

void print(Base b) {
    b.who();
}

int main() {
    Derived d;
    print(d);
}
```

### 代码讲解

- `void print(Base b)` 按值接收参数，这是切片发生的根源
- `print(d);` 传入 `Derived` 时，会先构造一个独立的 `Base` 对象副本
- 派生类那部分状态和动态类型信息在这里丢失
- 重点看：多态接口一旦按值传基类，就可能破坏多态

---

## 6. 为什么基类析构函数通常要写成虚函数？

### 核心答案

如果对象会通过基类指针删除，就必须让基类析构函数为虚函数，保证派生类析构被正确调用。


### English explanation

In an English interview, I would say:

If the object will be deleted through the base class pointer, the base class destructor must be a virtual function to ensure that the derived class destructor is called correctly.

### 错误回答示例

- “只要有继承就必须虚析构”
- “虚析构只是为了多态调用更优雅”
- “智能指针会自动解决这个问题，不需要虚析构”

### 面试官想听什么

- 你是否理解删除路径上的动态类型析构需求
- 你是否会区分“作为多态基类”与“仅作实现复用基类”

### 项目里怎么说

只要一个类被设计成多态基类，我会把析构函数设计成虚函数；如果不是多态基类，我不会机械地到处加虚析构，因为那会引入额外的对象模型成本。

### 深入解释

- 只有当对象可能经由基类指针或引用体系被销毁时，虚析构才是刚需
- 虚析构会让删除操作根据动态类型选择正确析构链
- 不是所有基类都必须虚析构，纯粹用于代码复用的非多态基类未必需要
- 面试中关键是能说清“为什么需要”而不是机械背结论

### 示例

```cpp
class Base {
public:
    virtual ~Base() = default;
};

class Derived : public Base {
public:
    ~Derived() override = default;
};
```

### 代码讲解

- `virtual ~Base() = default;` 是关键，表示通过基类销毁对象时要走动态析构链
- `~Derived() override` 明确派生类析构函数也在重写基类虚析构
- 这段代码重点看：多态基类最重要的不是有没有别的虚函数，而是析构路径是否正确

---

## 7. 什么是未定义行为？

### 核心答案

未定义行为表示标准不对程序结果做任何保证，结果可能看似正常，也可能在不同编译器、不同优化级别下完全不同。


### English explanation

In an English interview, I would say:

Undefined behavior means that the standard does not make any guarantees about program results. The results may appear normal, or they may be completely different under different compilers and different optimization levels.

### 错误回答示例

- “未定义行为就是程序会崩”
- “只要本机能跑就不算问题”
- “编译器会帮你兜底”

### 面试官想听什么

- 你是否理解 UB 会破坏优化前提
- 你是否知道常见 UB 类型，如越界、空指针解引用、访问已释放内存、数据竞争

### 项目里怎么说

面对潜在 UB，我不会用“线上目前没出事”来判断风险，而会尽量通过静态分析、sanitizer、边界检查和资源模型设计把这类问题提前消灭。

### 深入解释

- UB 最危险的地方在于结果不可预测，不仅可能崩溃，也可能悄悄产生错误结果
- 编译器优化常基于“程序没有 UB”这个前提，因此 UB 会让优化结果看起来非常反直觉
- 数据竞争在 C++ 里也是 UB，这一点经常被低估
- 学习 UB 的重点不是记例子，而是养成“不要依赖未被标准保证的行为”的习惯

### 示例

```cpp
int main() {
    int* p = nullptr;
    // int x = *p;
}
```

### 代码讲解

- `int* p = nullptr;` 创建一个空指针
- 注释掉的 `*p` 表示对空指针解引用
- 这正是典型未定义行为例子：代码可能崩，也可能表现得更隐蔽
- 重点看：UB 不是“结果固定错误”，而是“标准不保证任何结果”

---

## 8. C++ 内存模型是什么？

### 核心答案

C++ 内存模型定义了多线程程序中读写可见性、同步关系、数据竞争和重排序边界，是理解原子操作和 lock-free 设计的基础。


### English explanation

In an English interview, I would say:

The C++ memory model defines read and write visibility, synchronization relationships, data competition, and reordering boundaries in multi-threaded programs, and is the basis for understanding atomic operations and lock-free design.

### 错误回答示例

- “内存模型就是堆和栈”
- “只要用了 `atomic` 就不用考虑顺序”
- “内存模型只和操作系统有关”

### 面试官想听什么

- 你是否知道线程间可见性不是天然成立的
- 你是否知道 acquire/release 和 happens-before 这些概念

### 项目里怎么说

业务代码里我通常优先使用锁来换取简单正确；只有在确认热点瓶颈存在时，才会更深入地使用原子和更细的内存序控制。

### 深入解释

- 内存模型研究的是线程间读写是否可见、顺序是否被保证，而不是简单的“内存如何分配”
- 编译器和 CPU 都可能为了性能重排指令，这就是为什么线程同步必须由语言层明确定义
- `happens-before` 是理解线程安全的重要概念，它描述一个操作结果对另一个操作可见的顺序关系
- 不了解内存模型，原子代码很容易“看起来对，实际上错”

---

## 9. `memory_order_relaxed/acquire/release/seq_cst` 应该怎么理解？

### 核心答案

- `relaxed` 只保证原子性
- `release` 发布之前写入
- `acquire` 获取发布侧写入
- `seq_cst` 提供更强的全局一致观察顺序


### English explanation

In an English interview, I would say:

- `relaxed` only guarantees atomicity
- `release` written before release
- `acquire` Get publishing side writes
- `seq_cst` provides a stronger globally consistent observation order

### 错误回答示例

- “都用 `relaxed` 性能最好，所以最好”
- “`seq_cst` 一定最慢所以不能用”
- “有了 acquire/release 就不用再想数据流”

### 面试官想听什么

- 你是否知道内存序的核心是可见性和重排序约束
- 你是否会先追求正确性，再追求局部优化

### 项目里怎么说

除非我在写并发基础设施，否则我不会轻易下沉到复杂内存序调优。业务场景里，简单、可证明正确的同步方式通常比“理论上更快”的技巧更可靠。

### 深入解释

- `relaxed` 只保证单个原子操作本身不被撕裂，不保证跨线程观察顺序
- `release` 和 `acquire` 通常成对使用，用于建立发布-获取同步关系
- `seq_cst` 语义最强，也最容易解释，很多场景先从它开始是合理的
- 内存序越弱，推理越困难，因此“更快”并不自动意味着“更值得用”

### 示例

```cpp
#include <atomic>

std::atomic<bool> ready = false;
int data = 0;

void producer() {
    data = 42;
    ready.store(true, std::memory_order_release);
}

void consumer() {
    if (ready.load(std::memory_order_acquire)) {
        // 此处可见 producer 对 data 的写入
    }
}
```

### 代码讲解

- `ready.store(true, std::memory_order_release);` 发布写入结果
- `ready.load(std::memory_order_acquire)` 获取这次发布
- `data = 42;` 虽然不是原子变量，但在这组 release/acquire 同步关系下，消费者可见
- 这段代码重点看：内存序不是单看某一行，而是成对建立可见性关系

---

## 10. 什么是 type traits？

### 核心答案

type traits 是一组编译期工具，用来判断、查询或变换类型。


### English explanation

In an English interview, I would say:

Type traits are a set of compile-time tools used to determine, query, or transform types.

### 错误回答示例

- “traits 就是反射”
- “只有模板元编程才会用到”
- “现代 C++ 里都被 concepts 替代了”

### 面试官想听什么

- 你是否知道常见 traits，如 `is_integral`、`is_same`、`remove_reference`
- 你是否知道 traits 是很多泛型约束和实现分支的基础

### 项目里怎么说

在基础组件或通用模板工具中，我会用 traits 控制模板行为；在业务代码中则会克制使用，避免把简单逻辑写成过度技巧化的模板元编程。

### 深入解释

- traits 常见能力包括判断类型性质、移除修饰、生成关联类型
- 很多看似高级的模板技巧，其实底层都在依赖 traits 提供的类型信息
- 它们本质是编译期工具，不会产生运行时反射机制
- 面试中能把 traits 和泛型约束联系起来，通常就已经说明理解比较扎实

### 示例

```cpp
#include <type_traits>

static_assert(std::is_integral_v<int>);
static_assert(std::is_pointer_v<int*>);
static_assert(std::is_same_v<std::remove_reference_t<int&>, int>);
```

### 代码讲解

- `std::is_integral_v<int>` 判断类型是否为整型
- `std::is_pointer_v<int*>` 判断类型是否为指针
- `std::remove_reference_t<int&>` 去掉引用修饰，再与 `int` 比较
- 这段代码重点看：traits 是编译期类型查询和变换工具

---

## 11. `weak_ptr` 解决了什么问题？

### 核心答案

`weak_ptr` 用来观察 `shared_ptr` 管理的对象，但不参与拥有，主要用于打破循环引用。


### English explanation

In an English interview, I would say:

`weak_ptr` is used to observe objects managed by `shared_ptr`, but does not participate in ownership. It is mainly used to break circular references.

### 错误回答示例

- “`weak_ptr` 就是不安全的智能指针”
- “只要有 `shared_ptr` 就不需要 `weak_ptr`”
- “`weak_ptr` 能直接当普通指针用”

### 面试官想听什么

- 你是否理解引用计数环为什么会泄漏
- 你是否知道 `weak_ptr::lock()` 的用途

### 项目里怎么说

在双向关系、缓存和观察者模式里，我会显式把一侧定义成非拥有关系，用 `weak_ptr` 表达“知道它存在，但不负责延长生命周期”。

### 深入解释

- `shared_ptr` 循环引用问题的根源是引用计数无法降到 0
- `weak_ptr` 不增加强引用计数，因此能打破这种环
- 使用 `weak_ptr` 时通常要先 `lock()` 得到临时 `shared_ptr`，再安全访问对象
- 这一题面试官真正想听的是“你是否会区分拥有关系和观察关系”

### 示例

```cpp
#include <memory>

struct Node {
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;
};
```

### 代码讲解

- `next` 是拥有关系，会增加强引用计数
- `prev` 是观察关系，不会增加强引用计数
- 这正是双向关系中避免循环引用的典型设计
- 重点看：`weak_ptr` 的语义不是“弱一点的 shared_ptr”，而是“不拥有”

---

## 12. 为什么说 `shared_ptr` 不是“更高级的裸指针”？

### 核心答案

`shared_ptr` 的核心不是自动 delete，而是共享所有权语义。它有成本，也会改变对象生命周期模型。


### English explanation

In an English interview, I would say:

The core of `shared_ptr` is not automatic delete, but shared ownership semantics. It has a cost and changes the object lifecycle model.

### 错误回答示例

- “为了安全，所有指针都换成 `shared_ptr`”
- “`shared_ptr` 没有坏处，就是更方便”
- “只要引用计数归零就说明设计没问题”

### 面试官想听什么

- 你是否理解 `shared_ptr` 的引用计数、原子成本和循环引用风险
- 你是否知道所有权建模比“自动释放”更重要

### 项目里怎么说

我会把 `shared_ptr` 当成一种强语义工具，而不是默认容器。只有在对象确实被多个模块共同拥有，并且释放时机无法由单一拥有者决定时，我才会使用它。

### 深入解释

- `shared_ptr` 解决的是共享所有权，不是“普通指针自动释放”
- 一旦默认到处使用 `shared_ptr`，对象生命周期边界会变得模糊
- 这会让释放时机难以推导，也增加调试复杂度
- 所以现代 C++ 更强调先用 `unique_ptr` 建模，再看是否真的需要共享

---

## 13. 什么是 copy elision？RVO / NRVO 是什么？

### 核心答案

copy elision 是编译器省略拷贝或移动，直接在目标位置构造对象。RVO 和 NRVO 是常见返回值优化形式。


### English explanation

In an English interview, I would say:

Copy elision means that the compiler omits copying or moving and directly constructs the object at the target location. RVO and NRVO are common forms of return value optimization.

### 错误回答示例

- “按值返回对象一定很慢”
- “有移动构造之后就不需要返回值优化了”
- “RVO 只是编译器碰巧帮你快一点”

### 面试官想听什么

- 你是否知道现代 C++ 中按值返回对象通常是合理的
- 你是否知道 copy elision 让值语义设计更可行

### 项目里怎么说

我不会为了避免“想象中的拷贝”而到处返回裸指针或输出参数。只要对象语义清晰，按值返回通常是更自然也更现代的接口形式。

### 深入解释

- copy elision 让“返回对象”不一定意味着真的发生拷贝或移动
- RVO 指直接在调用方目标位置构造返回值，NRVO 是对具名局部变量的类似优化
- 这也是现代 C++ 倾向值语义接口的重要基础
- 因此很多老式“输出参数优先”的习惯在今天未必仍是最优设计

### 示例

```cpp
#include <string>

std::string makeText() {
    return "hello";
}

int main() {
    std::string s = makeText();
}
```

### 代码讲解

- `return "hello";` 返回一个按值构造的 `std::string`
- `std::string s = makeText();` 在现代编译器下常能直接构造到目标位置
- 重点看：按值返回对象在现代 C++ 里通常是自然且高效的

---

## 14. 模板元编程和 `if constexpr` 的关系是什么？

### 核心答案

`if constexpr` 让很多编译期分支逻辑比传统模板特化和 SFINAE 更直观、可读。


### English explanation

In an English interview, I would say:

`if constexpr` makes a lot of compile-time branching logic more intuitive and readable than traditional template specializations and SFINAE.

### 错误回答示例

- “有了 `if constexpr`，模板特化就没用了”
- “`if constexpr` 和运行时 if 一样”
- “编译期分支就是为了炫技”

### 面试官想听什么

- 你是否知道 `if constexpr` 会在编译期丢弃无效分支
- 你是否理解现代 C++ 正在把模板写法从技巧化转向可读化

### 项目里怎么说

如果只是根据类型差异做少量行为分支，我会优先 `if constexpr`；只有在接口选择或类型关系本身需要通过模板特化表达时，才会下沉到更复杂的模板技巧。

### 深入解释

- `if constexpr` 在编译期丢弃不成立分支，因此可以安全写出某些只对特定类型合法的代码
- 它显著降低了模板分支逻辑的阅读门槛
- 但它不是模板特化的完全替代品，某些类型级接口选择仍需特化
- 现代 C++ 的趋势是让泛型代码更像“正常代码”，而不是满是技巧性模板语法

### 示例

```cpp
#include <iostream>
#include <type_traits>

template <typename T>
void printInfo(const T& value) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "integral: " << value << '\n';
    } else {
        std::cout << "other\n";
    }
}
```

### 代码讲解

- `if constexpr (std::is_integral_v<T>)` 是编译期分支
- 当 `T` 是整型时，只保留第一条分支
- 否则编译器会丢弃不成立的分支
- 重点看：`if constexpr` 不是运行时 if，而是编译期按类型裁剪代码

---

## 15. 如何设计一个现代 C++ 风格的类？

### 核心答案

现代 C++ 风格的类通常强调：

- 所有权清晰
- 生命周期明确
- Rule of Zero 优先
- 接口简洁
- 异常安全可推导


### English explanation

In an English interview, I would say:

Modern C++ style classes usually emphasize:

- Clear ownership
- clear life cycle
- Rule of Zero priority
- Simple interface
- Exceptionally safe and derivable

### 错误回答示例

- “把所有成员 private、所有函数 inline 就叫现代 C++”
- “只要用了智能指针就是现代设计”
- “设计类就是先写一堆继承层级”

### 面试官想听什么

- 你是否把语言特性和工程约束结合起来
- 你是否理解现代风格首先是建模清晰，而不是语法花样

### 项目里怎么说

我设计类时会先问几个问题：谁拥有资源、能不能拷贝、能不能移动、是否需要多态、异常发生后状态要保证到什么程度。很多设计问题本质上都是这些问题的外化。

### 深入解释

- 现代 C++ 风格首先是建模清晰，而不是特性堆砌
- 好的类设计通常能从接口上直接看出所有权和生命周期约束
- 如果一个类必须依赖复杂约定才能安全使用，往往说明接口还不够好
- 设计类时从资源、不变量和错误处理出发，通常比从继承层级出发更稳

---

## 16. 单例在现代 C++ 中怎么写更合理？

### 核心答案

如果必须使用单例，函数内局部静态对象是现代 C++ 中最常见、最简单且线程安全的实现方式。


### English explanation

In an English interview, I would say:

If you must use a singleton, local static objects within a function are the most common, simplest, and thread-safe implementation in modern C++.

### 错误回答示例

- “单例是最佳实践，所有全局对象都该这么写”
- “自己加双重检查锁最专业”
- “局部静态只是语法糖，不可靠”

### 面试官想听什么

- 你是否知道 C++11 起局部静态初始化线程安全
- 你是否也能主动说出单例的缺点

### 项目里怎么说

如果能通过依赖注入、显式对象生命周期管理解决问题，我不会优先上单例；只有在配置中心、日志设施这类极少数全局资源场景，才会谨慎使用。

### 深入解释

- 函数局部静态单例的优势是实现简单，且自 C++11 起初始化线程安全
- 但单例天然带来全局状态、隐藏依赖和测试困难
- 因此面试中更好的回答通常不是“我会写单例”，而是“我知道怎么写，也知道什么时候不该用”
- 高质量回答应同时覆盖实现方式和架构代价

### 示例

```cpp
class Config {
public:
    static Config& instance() {
        static Config cfg;
        return cfg;
    }

    Config(const Config&) = delete;
    Config& operator=(const Config&) = delete;

private:
    Config() = default;
};
```

### 代码讲解

- `static Config cfg;` 是函数内局部静态对象
- `instance()` 每次返回同一个全局唯一实例引用
- 拷贝构造和赋值被 `delete`，防止复制出新的实例
- 这段代码重点看：单例关键不是语法花样，而是“唯一实例 + 受控访问入口”

---

## 高级篇复习建议

- 回答不要只停在定义，要讲设计动机和代价
- 凡是并发题，优先强调正确性和可证明性
- 凡是高级技巧题，尽量回到“什么时候真的值得用”
