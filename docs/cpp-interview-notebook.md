# C++ Interview Notebook

This notebook is organized by level:

- Beginner
- Intermediate
- Advanced

Each topic includes:

- a common interview question
- a short answer
- a code example

---

## Beginner

### 1. What is the difference between `stack` and `heap`?

**Answer**

The stack stores automatic local variables and is managed automatically by scope. The heap stores dynamically allocated objects and must be managed manually or with smart pointers.

**Example**

```cpp
#include <iostream>

int main() {
    int a = 10;          // stack
    int* b = new int(20); // heap

    std::cout << a << " " << *b << '\n';

    delete b;
}
```

### 2. What is the difference between a pointer and a reference?

**Answer**

A pointer can be null and can be reassigned. A reference must refer to an existing object after initialization and cannot be reseated.

**Example**

```cpp
#include <iostream>

int main() {
    int x = 10;
    int y = 20;

    int* p = &x;
    p = &y;

    int& r = x;
    r = y; // assigns value of y to x, does not rebind r

    std::cout << x << " " << y << '\n';
}
```

### 3. What is RAII?

**Answer**

RAII means Resource Acquisition Is Initialization. A resource is acquired in a constructor and released in a destructor, so lifetime is tied to scope.

**Example**

```cpp
#include <fstream>
#include <string>

int main() {
    std::ofstream out("log.txt");
    out << "hello\n";
} // file closes automatically here
```

### 4. What is the difference between `struct` and `class`?

**Answer**

The only language-level difference is the default access level:

- `struct`: public by default
- `class`: private by default

**Example**

```cpp
struct Point {
    int x;
    int y;
};

class Counter {
    int value = 0;

public:
    int get() const { return value; }
};
```

### 5. What are constructors and destructors?

**Answer**

A constructor initializes an object when it is created. A destructor runs when the object is destroyed and is typically used for cleanup.

**Example**

```cpp
#include <iostream>

class FileGuard {
public:
    FileGuard() { std::cout << "open\n"; }
    ~FileGuard() { std::cout << "close\n"; }
};

int main() {
    FileGuard guard;
}
```

### 6. What is function overloading?

**Answer**

Function overloading allows multiple functions with the same name but different parameter lists.

**Example**

```cpp
#include <iostream>

void print(int x) {
    std::cout << "int: " << x << '\n';
}

void print(double x) {
    std::cout << "double: " << x << '\n';
}

int main() {
    print(3);
    print(3.14);
}
```

### 7. What is the difference between pass-by-value, pass-by-reference, and pass-by-const-reference?

**Answer**

- Pass-by-value copies the argument.
- Pass-by-reference allows modification of the original object.
- Pass-by-const-reference avoids copying and prevents modification.

**Example**

```cpp
#include <iostream>
#include <string>

void byValue(std::string s) {
    s += "!";
}

void byRef(std::string& s) {
    s += "!";
}

void byConstRef(const std::string& s) {
    std::cout << s << '\n';
}

int main() {
    std::string msg = "hello";
    byValue(msg);
    byRef(msg);
    byConstRef(msg);
}
```

### 8. What is polymorphism?

**Answer**

Polymorphism allows calling derived-class behavior through a base-class interface, usually via `virtual` functions.

**Example**

```cpp
#include <iostream>
#include <memory>

class Animal {
public:
    virtual void speak() const {
        std::cout << "animal\n";
    }

    virtual ~Animal() = default;
};

class Dog : public Animal {
public:
    void speak() const override {
        std::cout << "woof\n";
    }
};

int main() {
    std::unique_ptr<Animal> pet = std::make_unique<Dog>();
    pet->speak();
}
```

### 9. What is the STL?

**Answer**

The STL is the Standard Template Library. It provides containers, iterators, algorithms, and function objects.

**Example**

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> nums = {4, 2, 5, 1, 3};
    std::sort(nums.begin(), nums.end());

    for (int n : nums) {
        std::cout << n << ' ';
    }
}
```

### 10. What is the difference between `vector` and `list`?

**Answer**

`std::vector` stores elements contiguously and supports fast random access. `std::list` is a doubly linked list with efficient insertion/removal in the middle if you already have an iterator.

**Example**

```cpp
#include <iostream>
#include <list>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};
    std::list<int> l = {1, 2, 3};

    std::cout << v[1] << '\n';
    std::cout << *std::next(l.begin()) << '\n';
}
```

---

## Intermediate

### 1. What are the Rule of Three, Rule of Five, and Rule of Zero?

**Answer**

- Rule of Three: if a class defines destructor, copy constructor, or copy assignment, it likely needs all three.
- Rule of Five: with move constructor and move assignment added in modern C++.
- Rule of Zero: prefer types that do not manually manage resources at all.

**Example**

```cpp
#include <memory>

class Buffer {
    std::unique_ptr<int[]> data;

public:
    explicit Buffer(size_t n) : data(std::make_unique<int[]>(n)) {}
};
```

This is Rule of Zero style because `std::unique_ptr` manages the resource.

### 2. What are lvalues and rvalues?

**Answer**

An lvalue has identity and can appear on the left-hand side of assignment. An rvalue is a temporary or movable value.

**Example**

```cpp
#include <string>

int main() {
    std::string a = "hello";      // a is an lvalue
    std::string b = a + " world"; // temporary result is an rvalue
}
```

### 3. What is move semantics?

**Answer**

Move semantics transfer ownership of resources from one object to another instead of copying them, which improves performance for expensive objects.

**Example**

```cpp
#include <iostream>
#include <string>
#include <utility>

int main() {
    std::string a = "large string";
    std::string b = std::move(a);

    std::cout << "b = " << b << '\n';
}
```

### 4. What are smart pointers and when should you use them?

**Answer**

- `std::unique_ptr`: exclusive ownership
- `std::shared_ptr`: shared ownership
- `std::weak_ptr`: non-owning observer for shared objects

**Example**

```cpp
#include <iostream>
#include <memory>

class Node {
public:
    int value;
    explicit Node(int v) : value(v) {}
};

int main() {
    auto p = std::make_unique<Node>(42);
    std::cout << p->value << '\n';
}
```

### 5. What is the difference between shallow copy and deep copy?

**Answer**

A shallow copy copies addresses or handles. A deep copy duplicates the underlying resource so both objects own independent state.

**Example**

```cpp
#include <cstring>
#include <iostream>

class Text {
    char* data;

public:
    Text(const char* s) {
        data = new char[std::strlen(s) + 1];
        std::strcpy(data, s);
    }

    Text(const Text& other) {
        data = new char[std::strlen(other.data) + 1];
        std::strcpy(data, other.data);
    }

    ~Text() {
        delete[] data;
    }
};
```

### 6. What are templates?

**Answer**

Templates allow writing generic code that works with multiple types.

**Example**

```cpp
#include <iostream>

template <typename T>
T maxValue(T a, T b) {
    return (a > b) ? a : b;
}

int main() {
    std::cout << maxValue(3, 7) << '\n';
    std::cout << maxValue(2.5, 1.5) << '\n';
}
```

### 7. What is the difference between `virtual`, `override`, and `final`?

**Answer**

- `virtual` declares a function for dynamic dispatch
- `override` checks that a derived function overrides a base virtual function
- `final` prevents further overriding or inheritance

**Example**

```cpp
class Base {
public:
    virtual void run() {}
};

class Derived final : public Base {
public:
    void run() override {}
};
```

### 8. What is the purpose of `constexpr`?

**Answer**

`constexpr` enables compile-time evaluation when possible, improving safety and sometimes performance.

**Example**

```cpp
#include <array>

constexpr int square(int x) {
    return x * x;
}

int main() {
    std::array<int, square(4)> arr{};
}
```

### 9. What is a race condition?

**Answer**

A race condition happens when multiple threads access shared data concurrently and at least one modifies it without proper synchronization.

**Example**

```cpp
#include <iostream>
#include <mutex>
#include <thread>

int counter = 0;
std::mutex mtx;

void increment() {
    for (int i = 0; i < 10000; ++i) {
        std::lock_guard<std::mutex> lock(mtx);
        ++counter;
    }
}

int main() {
    std::thread t1(increment);
    std::thread t2(increment);

    t1.join();
    t2.join();

    std::cout << counter << '\n';
}
```

### 10. What is the difference between `std::map` and `std::unordered_map`?

**Answer**

`std::map` is usually implemented as a balanced tree and keeps keys ordered. `std::unordered_map` is hash-based and does not keep ordering.

**Example**

```cpp
#include <iostream>
#include <map>
#include <unordered_map>

int main() {
    std::map<int, char> ordered = {{2, 'b'}, {1, 'a'}};
    std::unordered_map<int, char> hashed = {{2, 'b'}, {1, 'a'}};

    std::cout << ordered.begin()->first << '\n';
    std::cout << hashed.size() << '\n';
}
```

---

## Advanced

### 1. What is perfect forwarding?

**Answer**

Perfect forwarding preserves the value category of arguments when passing them through a template wrapper, usually with forwarding references and `std::forward`.

**Example**

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

### 2. What is SFINAE?

**Answer**

SFINAE means Substitution Failure Is Not An Error. During template substitution, invalid candidates can be removed from overload resolution instead of causing immediate compilation failure.

**Example**

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

int main() {
    printType(42);
    printType(3.14);
}
```

### 3. What is the difference between dynamic polymorphism and static polymorphism?

**Answer**

Dynamic polymorphism uses virtual dispatch at runtime. Static polymorphism is resolved at compile time, often through templates or CRTP.

**Example**

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

int main() {
    MessagePrinter p;
    p.print();
}
```

### 4. What is undefined behavior?

**Answer**

Undefined behavior means the C++ standard imposes no requirements on the program result. The program may appear to work, crash, or behave inconsistently.

**Example**

```cpp
#include <iostream>

int main() {
    int* p = nullptr;
    // std::cout << *p << '\n'; // undefined behavior
}
```

### 5. What is the memory model in C++?

**Answer**

The memory model defines how threads interact through memory, including synchronization, visibility, and ordering constraints. It is the basis for atomics and lock-free programming.

**Example**

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
        // data is now visible here
    }
}
```

### 6. What are type traits?

**Answer**

Type traits are compile-time utilities that inspect or transform types, such as checking whether a type is integral or removing references.

**Example**

```cpp
#include <iostream>
#include <type_traits>

int main() {
    std::cout << std::is_pointer<int*>::value << '\n';
    std::cout << std::is_pointer<int>::value << '\n';
}
```

### 7. What problem does `std::weak_ptr` solve?

**Answer**

`std::weak_ptr` breaks ownership cycles created by `std::shared_ptr` and allows observing an object without extending its lifetime.

**Example**

```cpp
#include <memory>

struct Node {
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;
};
```

### 8. What is object slicing?

**Answer**

Object slicing happens when a derived object is copied into a base object by value, causing the derived part to be discarded.

**Example**

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
    print(d); // slicing
}
```

### 9. What is the difference between `new/delete` and smart pointers in modern C++?

**Answer**

Manual `new/delete` is error-prone and can lead to leaks or double frees. Smart pointers encode ownership in types and automate cleanup.

**Example**

```cpp
#include <memory>

class Engine {};

int main() {
    auto engine = std::make_unique<Engine>();
}
```

### 10. How would you design a thread-safe singleton in modern C++?

**Answer**

The usual modern approach is a function-local static object, because initialization is guaranteed to be thread-safe since C++11.

**Example**

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

---

## Common Follow-Up Questions

These are useful if you want to expand the notebook later:

- Why is a virtual destructor needed in base classes?
- What is the difference between `emplace_back` and `push_back`?
- When should you use `explicit`?
- What is the difference between `const` pointer and pointer to `const`?
- What is copy elision?
- What is the difference between `mutex`, `shared_mutex`, and `atomic`?
- What is the difference between C and C++ memory management?
- What is ABI and why can it matter in C++ projects?
- What are common STL iterator invalidation rules?
- What is the pimpl idiom?

## Suggested Next Expansion

If you want to make this notebook stronger for real interviews, the next sections should be:

1. Coding exercises with model solutions
2. System design questions for C++ backend roles
3. Debugging and performance tuning questions
4. C++17/C++20 feature summary
5. Common mistakes and anti-patterns
