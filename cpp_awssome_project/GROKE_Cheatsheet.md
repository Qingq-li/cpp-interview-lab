# GROKE C++ Interview Cheatsheet

This cheatsheet is for spoken C++ interview practice. Each answer is written so you can remember the keyword first, then speak the full answer naturally.

# Quick Memory Tables

### Pointer vs Reference

| Topic | Pointer | Reference |
|---|---|---|
| Null value | Can be null | Should refer to a valid object |
| Rebinding | Can point to another object | Cannot be rebound after initialization |
| Syntax | Uses `*` and `->` | Uses normal object syntax |
| Best use | Optional object, arrays, ownership APIs | Required object, clean parameter passing |

### Smart Pointer Choice

| Tool | Ownership Meaning | Interview Rule |
|---|---|---|
| Raw pointer | Non-owning or low-level view | Do not imply ownership |
| `std::unique_ptr` | Single owner | Default owning pointer |
| `std::shared_ptr` | Shared ownership | Use only when lifetime is truly shared |
| `std::weak_ptr` | Non-owning observer of shared object | Break cycles and observe safely |

### Container Choice

| Container | Strength | Cost / Risk |
|---|---|---|
| `std::vector` | Cache-friendly, fast iteration | Insert/erase in middle is expensive |
| `std::deque` | Fast push front and back | Less cache-friendly than vector |
| `std::list` | Stable iterators, cheap splice | Poor cache locality, extra allocation |
| `std::map` | Ordered keys, stable logarithmic lookup | Tree overhead |
| `std::unordered_map` | Average constant-time lookup | Hashing cost and rehash invalidation |

### Copy vs Move

| Operation | Meaning | Typical Cost |
|---|---|---|
| Copy | Duplicate the value/resource | Can allocate or deep-copy |
| Move | Transfer resources from source to target | Usually cheap pointer/state transfer |
| Copy elision | Construct directly in destination | No copy or move needed |

### Mutex vs Atomic

| Tool | Best For | Warning |
|---|---|---|
| `std::mutex` | Protecting multi-step invariants | Can deadlock if lock order is bad |
| `std::atomic` | Simple lock-free shared values | Memory ordering must be understood |
| `std::condition_variable` | Waiting for state change | Always wait with a predicate |

---

# Basic C++ Questions

## 1. What is the difference between C and C++?

| Field | Content |
|---|---|
| Question | What is the difference between C and C++? |
| Answer Keyword | C with abstraction; object lifetime; zero-cost abstractions |
| Answer Sentences | C++ supports the low-level control of C, but adds stronger abstraction tools such as classes, RAII, templates, overloading, and the standard library. In an interview I would say C++ is not just C with classes; modern C++ focuses on expressing ownership, lifetime, and type safety while still allowing high performance. |

## 2. What is RAII in C++?

| Field | Content |
|---|---|
| Question | What is RAII in C++? |
| Answer Keyword | Lifetime owns resource; destructor releases |
| Answer Sentences | RAII means a resource is tied to an object's lifetime. I acquire the resource in a constructor or factory function and release it in the destructor, so cleanup happens automatically even when exceptions occur. In production C++, this is the foundation of safe memory, file, lock, and socket management. |

| Resource | RAII Wrapper |
|---|---|
| Dynamic memory | `std::unique_ptr`, `std::shared_ptr` |
| Mutex lock | `std::lock_guard`, `std::unique_lock` |
| File handle | `std::fstream` or a custom RAII wrapper |

## 3. Why is the destructor important in C++?

| Field | Content |
|---|---|
| Question | Why is the destructor important in C++? |
| Answer Keyword | Cleanup at lifetime end |
| Answer Sentences | A destructor defines what happens when an object leaves scope or is deleted. It is important because C++ uses deterministic lifetime, so destructors are the normal place to release resources. A good destructor should usually not throw because it may run during exception unwinding. |

## 4. What is the difference between stack and heap memory?

| Field | Content |
|---|---|
| Question | What is the difference between stack and heap memory? |
| Answer Keyword | Automatic lifetime vs dynamic lifetime |
| Answer Sentences | Stack objects have automatic lifetime and are destroyed when the scope exits. Heap objects have dynamic lifetime and must be owned by something, normally a smart pointer or container. I prefer stack objects and RAII wrappers first because they make lifetime clearer and reduce leaks. |

| Memory Area | Lifetime | Typical Use |
|---|---|---|
| Stack | Scope-bound | Local variables, small objects |
| Heap | Manually/RAII-managed | Large objects, polymorphic objects, dynamic lifetime |

## 5. What is the difference between a pointer and a reference?

| Field | Content |
|---|---|
| Question | What is the difference between a pointer and a reference? |
| Answer Keyword | Nullable/rebindable vs required alias |
| Answer Sentences | A pointer can be null and can be changed to point to another object. A reference should be initialized to a valid object and cannot be rebound. For function parameters, I use references when the argument is required and pointers when null or optional behavior is meaningful. |

## 6. What is `const` correctness?

| Field | Content |
|---|---|
| Question | What is `const` correctness? |
| Answer Keyword | Promise not to modify; API contract |
| Answer Sentences | `const` correctness means using `const` to express which objects or parameters are not modified. It makes APIs safer and easier to reason about because callers know what can change. In class design, a `const` member function should not modify the logical state of the object. |

## 7. Explain the different meanings of `const` with pointers.

| Field | Content |
|---|---|
| Question | Explain the different meanings of `const` with pointers. |
| Answer Keyword | Pointer const vs pointee const |
| Answer Sentences | `const int*` means the integer cannot be modified through the pointer. `int* const` means the pointer itself cannot be reassigned. `const int* const` means both the pointed value and the pointer variable are const. |

| Syntax | Meaning |
|---|---|
| `const int* p` | Pointer to const int |
| `int const* p` | Same as pointer to const int |
| `int* const p` | Const pointer to int |
| `const int* const p` | Const pointer to const int |

## 8. What is the difference between declaration and definition?

| Field | Content |
|---|---|
| Question | What is the difference between declaration and definition? |
| Answer Keyword | Introduce name vs allocate/implement |
| Answer Sentences | A declaration introduces a name and type to the compiler. A definition provides the storage or implementation. For example, a function prototype is a declaration, while the function body is the definition. |

## 9. What is the One Definition Rule?

| Field | Content |
|---|---|
| Question | What is the One Definition Rule? |
| Answer Keyword | One definition across program |
| Answer Sentences | The One Definition Rule says that entities like non-inline functions and global variables must have exactly one definition in the program. Violating it can cause linker errors or undefined behavior. In practice, I keep definitions in source files and declarations in headers, unless the function is `inline`, a template, or a permitted header definition. |

## 10. What is the difference between `struct` and `class` in C++?

| Field | Content |
|---|---|
| Question | What is the difference between `struct` and `class` in C++? |
| Answer Keyword | Default access only |
| Answer Sentences | In C++, the technical difference is default access: `struct` defaults to public and `class` defaults to private. By convention, I use `struct` for simple data aggregates and `class` for types with invariants and behavior. |

## 11. What is object lifetime?

| Field | Content |
|---|---|
| Question | What is object lifetime? |
| Answer Keyword | Construction to destruction |
| Answer Sentences | Object lifetime is the period during which an object exists and can be safely used. It begins after construction and ends when the destructor starts or storage is released. Many C++ bugs come from using objects before lifetime begins or after lifetime ends. |

## 12. What is undefined behavior?

| Field | Content |
|---|---|
| Question | What is undefined behavior? |
| Answer Keyword | No language guarantee |
| Answer Sentences | Undefined behavior means the C++ standard gives no guarantee about what the program will do. Examples include out-of-bounds access, use-after-free, data races, and signed integer overflow. I avoid it by using standard containers, clear ownership, sanitizers, and careful concurrency rules. |

## 13. What is the difference between initialization and assignment?

| Field | Content |
|---|---|
| Question | What is the difference between initialization and assignment? |
| Answer Keyword | Create object vs replace value |
| Answer Sentences | Initialization creates an object with an initial value. Assignment changes the value of an object that already exists. This matters because constructors control initialization, while assignment operators control replacement after construction. |

## 14. What are constructors?

| Field | Content |
|---|---|
| Question | What are constructors? |
| Answer Keyword | Build valid object |
| Answer Sentences | Constructors initialize an object and establish its invariants. A good constructor leaves the object in a valid, usable state or fails clearly, often by throwing an exception. I prefer member initializer lists because they construct members directly. |

## 15. Why use a member initializer list?

| Field | Content |
|---|---|
| Question | Why use a member initializer list? |
| Answer Keyword | Direct construction |
| Answer Sentences | A member initializer list constructs members directly instead of default-constructing and then assigning them. It is required for references, `const` members, and members without default constructors. It is also usually clearer and more efficient. |

## 16. What is function overloading?

| Field | Content |
|---|---|
| Question | What is function overloading? |
| Answer Keyword | Same name, different parameters |
| Answer Sentences | Function overloading means multiple functions share the same name but have different parameter lists. The compiler selects the best match at compile time. Return type alone is not enough to overload a function because call resolution would be ambiguous. |

## 17. What is operator overloading?

| Field | Content |
|---|---|
| Question | What is operator overloading? |
| Answer Keyword | Natural syntax for user types |
| Answer Sentences | Operator overloading lets a user-defined type support operators like `+`, `==`, or `<`. I use it when the operator has an obvious meaning for the type. I avoid surprising behavior because overloaded operators should make code clearer, not cleverer. |

## 18. What is an lvalue and an rvalue?

| Field | Content |
|---|---|
| Question | What is an lvalue and an rvalue? |
| Answer Keyword | Has identity vs temporary value |
| Answer Sentences | An lvalue is an expression with identity, usually something you can take the address of. An rvalue is typically a temporary or a value that can be moved from. This distinction matters for overload resolution, move semantics, and perfect forwarding. |

## 19. What does `auto` do?

| Field | Content |
|---|---|
| Question | What does `auto` do? |
| Answer Keyword | Compiler deduces type |
| Answer Sentences | `auto` asks the compiler to deduce the variable type from the initializer. It reduces repetition, especially with iterators and templates, but I avoid it when it hides important ownership or conversion behavior. I still use explicit types when readability is better. |

## 20. What is the difference between `auto`, `auto&`, and `const auto&`?

| Field | Content |
|---|---|
| Question | What is the difference between `auto`, `auto&`, and `const auto&`? |
| Answer Keyword | Copy, mutable reference, read-only reference |
| Answer Sentences | `auto` usually makes a copy. `auto&` binds to the original object and allows modification. `const auto&` binds without copying and prevents modification, which is often good for iterating over large objects. |

---

# Ownership, RAII, and Special Member Functions

## 21. What is the Rule of Zero?

| Field | Content |
|---|---|
| Question | What is the Rule of Zero? |
| Answer Keyword | Let members manage resources |
| Answer Sentences | The Rule of Zero says a class should not define custom destructors, copy, or move operations unless it directly manages a resource. Instead, use members like `std::vector`, `std::string`, and smart pointers that already manage resources correctly. This makes classes simpler and safer. |

## 22. What is the Rule of Three?

| Field | Content |
|---|---|
| Question | What is the Rule of Three? |
| Answer Keyword | Destructor, copy constructor, copy assignment |
| Answer Sentences | The Rule of Three says that if a class needs a custom destructor, it probably also needs a custom copy constructor and copy assignment operator. This is because the class likely owns a resource, and copying must define whether the resource is deep-copied, shared, or disabled. |

## 23. What is the Rule of Five?

| Field | Content |
|---|---|
| Question | What is the Rule of Five? |
| Answer Keyword | Add move constructor and move assignment |
| Answer Sentences | The Rule of Five extends the Rule of Three by adding the move constructor and move assignment operator. If a class owns a resource, move operations can transfer ownership efficiently. In modern C++, I still prefer the Rule of Zero when possible. |

## 24. What is a copy constructor?

| Field | Content |
|---|---|
| Question | What is a copy constructor? |
| Answer Keyword | Construct from same type |
| Answer Sentences | A copy constructor creates a new object from an existing object of the same type. It is used when passing by value, returning objects in some cases, or explicitly copying. For resource-owning classes, it must define correct ownership behavior. |

## 25. What is a move constructor?

| Field | Content |
|---|---|
| Question | What is a move constructor? |
| Answer Keyword | Steal resources safely |
| Answer Sentences | A move constructor creates a new object by taking resources from a temporary or movable source. It should leave the source object valid but unspecified. Move construction is important for efficient containers and return values. |

## 26. What does `std::move` actually do?

| Field | Content |
|---|---|
| Question | What does `std::move` actually do? |
| Answer Keyword | Cast to rvalue reference |
| Answer Sentences | `std::move` does not move anything by itself. It casts an expression to an rvalue reference, allowing move constructors or move assignment operators to be selected. The actual move happens inside the target operation. |

## 27. When should you use `std::unique_ptr`?

| Field | Content |
|---|---|
| Question | When should you use `std::unique_ptr`? |
| Answer Keyword | Exclusive ownership |
| Answer Sentences | I use `std::unique_ptr` when exactly one owner is responsible for an object. It makes ownership explicit and automatically deletes the object when the pointer goes out of scope. It is my default choice for dynamic ownership unless sharing is truly required. |

## 28. When should you use `std::shared_ptr`?

| Field | Content |
|---|---|
| Question | When should you use `std::shared_ptr`? |
| Answer Keyword | Shared lifetime |
| Answer Sentences | I use `std::shared_ptr` only when multiple owners must keep an object alive independently. It has overhead from reference counting and can create cycles, so it should not be used just to avoid thinking about ownership. If there is no shared lifetime, `std::unique_ptr` or references are better. |

## 29. What problem does `std::weak_ptr` solve?

| Field | Content |
|---|---|
| Question | What problem does `std::weak_ptr` solve? |
| Answer Keyword | Observe without owning |
| Answer Sentences | `std::weak_ptr` observes an object managed by `std::shared_ptr` without increasing the reference count. It helps break ownership cycles and lets code check whether the object is still alive using `lock()`. It is useful for caches, callbacks, and parent-child relationships where ownership should not be circular. |

## 30. What is a dangling pointer or dangling reference?

| Field | Content |
|---|---|
| Question | What is a dangling pointer or dangling reference? |
| Answer Keyword | Refers to destroyed object |
| Answer Sentences | A dangling pointer or reference refers to an object whose lifetime has ended. Using it is undefined behavior. I avoid this by keeping ownership clear, avoiding references to temporaries, and using tools like sanitizers during testing. |

## 31. What is shallow copy vs deep copy?

| Field | Content |
|---|---|
| Question | What is shallow copy vs deep copy? |
| Answer Keyword | Copy handle vs copy owned data |
| Answer Sentences | A shallow copy copies only handles or pointers, so two objects may refer to the same resource. A deep copy duplicates the underlying resource so each object owns independent state. For owning classes, the correct choice depends on the desired ownership semantics. |

## 32. Why should base classes often have virtual destructors?

| Field | Content |
|---|---|
| Question | Why should base classes often have virtual destructors? |
| Answer Keyword | Delete derived through base safely |
| Answer Sentences | If a class is intended to be used polymorphically, its destructor should usually be virtual. Otherwise deleting a derived object through a base pointer can cause undefined behavior because the derived destructor may not run. A virtual destructor ensures complete cleanup. |

---

# Modern C++ Language Features

## 33. What is `nullptr` and why is it better than `NULL`?

| Field | Content |
|---|---|
| Question | What is `nullptr` and why is it better than `NULL`? |
| Answer Keyword | Type-safe null pointer |
| Answer Sentences | `nullptr` is a real null pointer value with type `std::nullptr_t`. It is better than `NULL` because `NULL` may be an integer constant and can confuse overload resolution. In modern C++, I use `nullptr` consistently. |

## 34. What is `constexpr`?

| Field | Content |
|---|---|
| Question | What is `constexpr`? |
| Answer Keyword | Compile-time capable expression |
| Answer Sentences | `constexpr` means a value or function can be evaluated at compile time when its inputs are compile-time constants. It can improve safety and performance by moving work to compile time. It also documents that the function has restrictions compatible with constant evaluation. |

## 35. What is the difference between `const` and `constexpr`?

| Field | Content |
|---|---|
| Question | What is the difference between `const` and `constexpr`? |
| Answer Keyword | Read-only vs compile-time |
| Answer Sentences | `const` means a value cannot be modified through that name. `constexpr` means the value or function can participate in compile-time evaluation. Every `constexpr` variable is const, but not every `const` variable is known at compile time. |

## 36. What is `static` used for in C++?

| Field | Content |
|---|---|
| Question | What is `static` used for in C++? |
| Answer Keyword | Storage duration, linkage, class member |
| Answer Sentences | `static` has several meanings depending on context. A static local variable keeps its value between calls. A static class member belongs to the class rather than each object. At namespace scope, `static` gives internal linkage, though unnamed namespaces are often preferred. |

## 37. What is `inline` used for?

| Field | Content |
|---|---|
| Question | What is `inline` used for? |
| Answer Keyword | Multiple definitions allowed in headers |
| Answer Sentences | Historically, `inline` suggested inlining to the compiler, but its important language meaning is allowing the same function definition in multiple translation units. This is useful for header-defined functions. The compiler still decides whether to actually inline machine code. |

## 38. What is `explicit` used for?

| Field | Content |
|---|---|
| Question | What is `explicit` used for? |
| Answer Keyword | Prevent accidental conversion |
| Answer Sentences | `explicit` prevents constructors or conversion operators from being used for implicit conversions. I use it for single-argument constructors unless implicit conversion is truly intended. It makes APIs safer by avoiding surprising object creation. |

## 39. What is `std::optional`?

| Field | Content |
|---|---|
| Question | What is `std::optional`? |
| Answer Keyword | Value may be absent |
| Answer Sentences | `std::optional<T>` represents either a `T` value or no value. It is useful when absence is a normal result, not an error. It is often clearer than using a magic value or a nullable pointer for non-owning data. |

## 40. What is `std::variant`?

| Field | Content |
|---|---|
| Question | What is `std::variant`? |
| Answer Keyword | Type-safe union |
| Answer Sentences | `std::variant` stores one value from a fixed set of possible types. It is a type-safe alternative to unions and can model state or messages without inheritance. I usually access it with `std::visit` or checked alternatives. |

## 41. What is `std::string_view`?

| Field | Content |
|---|---|
| Question | What is `std::string_view`? |
| Answer Keyword | Non-owning string view |
| Answer Sentences | `std::string_view` is a lightweight non-owning view of character data. It avoids copying when a function only needs to read a string. The key risk is lifetime: the viewed data must outlive the `string_view`. |

## 42. What is `std::span`?

| Field | Content |
|---|---|
| Question | What is `std::span`? |
| Answer Keyword | Non-owning contiguous range |
| Answer Sentences | `std::span` is a non-owning view over contiguous elements. It lets APIs accept arrays, vectors, or buffers without copying and without exposing ownership. Like `string_view`, it requires the underlying data to outlive the span. |

| Type | Meaning | Owns Data? |
|---|---|---|
| `std::string` | String storage | Yes |
| `std::string_view` | View of string data | No |
| `std::vector<T>` | Dynamic contiguous storage | Yes |
| `std::span<T>` | View of contiguous data | No |

## 43. What is structured binding?

| Field | Content |
|---|---|
| Question | What is structured binding? |
| Answer Keyword | Unpack tuple-like values |
| Answer Sentences | Structured binding lets me unpack pairs, tuples, arrays, or structs into named variables. It improves readability when working with return values like `std::pair`. I still watch whether I am copying or binding by reference. |

## 44. What is lambda capture?

| Field | Content |
|---|---|
| Question | What is lambda capture? |
| Answer Keyword | Bring external variables into lambda |
| Answer Sentences | Lambda capture controls how a lambda uses variables from the surrounding scope. Capturing by value copies the variable, while capturing by reference refers to the original variable. I choose capture carefully because it affects lifetime, thread safety, and mutability. |

---

# Polymorphism and Object-Oriented C++

## 45. What is polymorphism in C++?

| Field | Content |
|---|---|
| Question | What is polymorphism in C++? |
| Answer Keyword | Same interface, different behavior |
| Answer Sentences | Polymorphism means code can work through a common interface while different concrete types provide different behavior. In C++, runtime polymorphism is usually implemented with virtual functions, while compile-time polymorphism can be implemented with templates. |

## 46. What is a virtual function?

| Field | Content |
|---|---|
| Question | What is a virtual function? |
| Answer Keyword | Runtime dispatch |
| Answer Sentences | A virtual function is resolved at runtime based on the dynamic type of the object. It allows derived classes to override behavior through a base-class interface. The tradeoff is a small dispatch cost and usually one vtable pointer per polymorphic object. |

## 47. What is the difference between overload, override, and hide?

| Field | Content |
|---|---|
| Question | What is the difference between overload, override, and hide? |
| Answer Keyword | Same scope, virtual replacement, name hiding |
| Answer Sentences | Overload means functions with the same name but different parameter lists in the same scope. Override means a derived virtual function replaces a base virtual function with a matching signature. Name hiding happens when a derived declaration hides base overloads, which can surprise people unless `using Base::name` is used. |

| Term | Meaning | Compile/Runtime |
|---|---|---|
| Overload | Same name, different parameters | Compile time |
| Override | Derived virtual implementation | Runtime dispatch |
| Hide | Derived name hides base name | Compile-time lookup |

## 48. Why use the `override` keyword?

| Field | Content |
|---|---|
| Question | Why use the `override` keyword? |
| Answer Keyword | Compiler checks virtual override |
| Answer Sentences | `override` tells the compiler that a function must override a virtual function from the base class. If the signature is wrong, compilation fails. I use it consistently because it prevents subtle bugs from typos, missing `const`, or parameter mismatch. |

## 49. What is an abstract class?

| Field | Content |
|---|---|
| Question | What is an abstract class? |
| Answer Keyword | Has pure virtual function |
| Answer Sentences | An abstract class has at least one pure virtual function and cannot be instantiated directly. It defines an interface or partial implementation for derived classes. In C++, interfaces are often represented by abstract classes with virtual destructors. |

## 50. What is object slicing?

| Field | Content |
|---|---|
| Question | What is object slicing? |
| Answer Keyword | Derived part lost by value copy |
| Answer Sentences | Object slicing happens when a derived object is copied into a base object by value. The derived-specific state is lost, and virtual behavior may no longer work as expected. I avoid slicing by using references, pointers, or smart pointers for polymorphic objects. |

## 51. When should inheritance be used?

| Field | Content |
|---|---|
| Question | When should inheritance be used? |
| Answer Keyword | Is-a relationship and polymorphic interface |
| Answer Sentences | I use inheritance when there is a real is-a relationship or when runtime polymorphism is needed. For code reuse alone, composition is often better because it creates less coupling. A good base class should have a clear and stable contract. |

## 52. What is multiple inheritance?

| Field | Content |
|---|---|
| Question | What is multiple inheritance? |
| Answer Keyword | Derive from multiple bases |
| Answer Sentences | Multiple inheritance means a class derives from more than one base class. It can be useful for interface-style bases, but it can also create complexity such as ambiguity and diamond inheritance. I would use it carefully and keep interfaces small. |

## 53. What is the diamond problem?

| Field | Content |
|---|---|
| Question | What is the diamond problem? |
| Answer Keyword | Shared base duplicated |
| Answer Sentences | The diamond problem occurs when a class inherits from two classes that both inherit from the same base. Without virtual inheritance, the final object may contain two base subobjects. Virtual inheritance can solve this, but it adds complexity, so design should be reconsidered first. |

---

# STL Containers, Algorithms, and Iterators

## 54. Why is `std::vector` often the default container?

| Field | Content |
|---|---|
| Question | Why is `std::vector` often the default container? |
| Answer Keyword | Contiguous, cache-friendly, simple |
| Answer Sentences | `std::vector` stores elements contiguously, which makes iteration very cache-friendly. It has efficient random access and amortized constant-time `push_back`. Unless I need special ordering, stable iterators, or fast front insertion, `vector` is usually my first choice. |

## 55. What invalidates vector iterators?

| Field | Content |
|---|---|
| Question | What invalidates vector iterators? |
| Answer Keyword | Reallocation and erase |
| Answer Sentences | If a vector reallocation happens, all pointers, references, and iterators to its elements are invalidated. Insert or erase in the middle can also invalidate iterators at or after the change point. I avoid storing long-lived iterators across modifications unless the container guarantees it. |

## 56. What is the difference between `size()` and `capacity()`?

| Field | Content |
|---|---|
| Question | What is the difference between `size()` and `capacity()`? |
| Answer Keyword | Used elements vs allocated space |
| Answer Sentences | `size()` is the number of elements currently in the vector. `capacity()` is how many elements can fit before the vector reallocates. Calling `reserve()` can reduce reallocations when the approximate final size is known. |

## 57. What is the difference between `reserve()` and `resize()`?

| Field | Content |
|---|---|
| Question | What is the difference between `reserve()` and `resize()`? |
| Answer Keyword | Allocate capacity vs change size |
| Answer Sentences | `reserve()` changes capacity but does not create elements or change size. `resize()` changes the number of elements and may construct or destroy elements. I use `reserve()` for performance and `resize()` when the logical size should change. |

## 58. When would you choose `std::map` over `std::unordered_map`?

| Field | Content |
|---|---|
| Question | When would you choose `std::map` over `std::unordered_map`? |
| Answer Keyword | Ordered traversal and predictable logarithmic behavior |
| Answer Sentences | I choose `std::map` when I need ordered keys, range queries, or stable logarithmic behavior. I choose `std::unordered_map` when average lookup speed matters and ordering is not needed. I also consider hash quality, memory overhead, and rehashing. |

## 59. What is iterator invalidation?

| Field | Content |
|---|---|
| Question | What is iterator invalidation? |
| Answer Keyword | Iterator no longer safe |
| Answer Sentences | Iterator invalidation means an iterator, pointer, or reference no longer refers safely to the intended element after a container operation. Different containers have different invalidation rules. Good C++ code respects these rules, especially during insert, erase, and reallocation. |

## 60. Why use standard algorithms instead of hand-written loops?

| Field | Content |
|---|---|
| Question | Why use standard algorithms instead of hand-written loops? |
| Answer Keyword | Intent, correctness, reuse |
| Answer Sentences | Standard algorithms express intent more directly, such as `std::find`, `std::sort`, or `std::remove_if`. They are well-tested and often optimized. I still use loops when the control flow is clearer than forcing an algorithm. |

## 61. What is the erase-remove idiom?

| Field | Content |
|---|---|
| Question | What is the erase-remove idiom? |
| Answer Keyword | Move unwanted elements then erase tail |
| Answer Sentences | The erase-remove idiom removes elements from sequence containers like vector. `std::remove_if` moves the kept elements forward and returns the new logical end, then `erase` removes the leftover tail. In C++20, `std::erase_if` often makes this simpler. |

## 62. What is the complexity of binary search?

| Field | Content |
|---|---|
| Question | What is the complexity of binary search? |
| Answer Keyword | Sorted range, O(log n) comparisons |
| Answer Sentences | Binary search performs `O(log n)` comparisons, but it requires a sorted range. With random-access iterators it is efficient for indexing, while with non-random-access iterators iterator movement may still be costly. The precondition is important: the range must be sorted according to the same comparison. |

## 63. What is the difference between `emplace_back` and `push_back`?

| Field | Content |
|---|---|
| Question | What is the difference between `emplace_back` and `push_back`? |
| Answer Keyword | Construct in place vs insert object |
| Answer Sentences | `push_back` inserts an existing object by copy or move. `emplace_back` constructs the element directly inside the container from constructor arguments. `emplace_back` can avoid a temporary, but `push_back` can be clearer when an object already exists. |

---

# Templates and Type System

## 64. What are templates in C++?

| Field | Content |
|---|---|
| Question | What are templates in C++? |
| Answer Keyword | Compile-time generic code |
| Answer Sentences | Templates let me write generic code that works for many types. The compiler generates type-specific code when the template is instantiated. This gives high performance and type safety, but errors can be harder to read if constraints are unclear. |

## 65. What is template instantiation?

| Field | Content |
|---|---|
| Question | What is template instantiation? |
| Answer Keyword | Generate concrete code |
| Answer Sentences | Template instantiation happens when the compiler creates a concrete function or class from a template and specific template arguments. For example, `std::vector<int>` and `std::vector<double>` are different instantiations. This is why template definitions usually need to be visible in headers. |

## 66. What is type deduction?

| Field | Content |
|---|---|
| Question | What is type deduction? |
| Answer Keyword | Compiler infers template or auto type |
| Answer Sentences | Type deduction is when the compiler infers a type from an initializer or function argument. It is used by `auto`, templates, and generic lambdas. Understanding deduction is important because references and `const` qualifiers may be preserved or dropped depending on the context. |

## 67. What is perfect forwarding?

| Field | Content |
|---|---|
| Question | What is perfect forwarding? |
| Answer Keyword | Preserve value category |
| Answer Sentences | Perfect forwarding passes arguments to another function while preserving whether each argument was an lvalue or rvalue. It uses forwarding references and `std::forward`. This is useful in wrappers, factories, and generic code, but it should be used only when that flexibility is needed. |

## 68. What is the difference between `std::move` and `std::forward`?

| Field | Content |
|---|---|
| Question | What is the difference between `std::move` and `std::forward`? |
| Answer Keyword | Always rvalue vs conditional forwarding |
| Answer Sentences | `std::move` unconditionally casts to an rvalue reference. `std::forward` conditionally preserves the original value category of a forwarding reference. I use `std::move` when I am done with an object, and `std::forward` inside generic forwarding code. |

## 69. What is SFINAE?

| Field | Content |
|---|---|
| Question | What is SFINAE? |
| Answer Keyword | Invalid substitution removes overload |
| Answer Sentences | SFINAE means substitution failure is not an error. During template overload resolution, if substituting template arguments makes one candidate invalid, that candidate can be removed instead of causing compilation to fail. Modern C++ often uses concepts or `requires` clauses because they express constraints more clearly. |

## 70. What are C++20 concepts?

| Field | Content |
|---|---|
| Question | What are C++20 concepts? |
| Answer Keyword | Named template constraints |
| Answer Sentences | Concepts define constraints on template parameters. They make generic code easier to read and produce clearer compiler errors than older SFINAE techniques. I see them as a way to document and enforce what operations a template expects from a type. |

## 71. What is `if constexpr`?

| Field | Content |
|---|---|
| Question | What is `if constexpr`? |
| Answer Keyword | Compile-time branch |
| Answer Sentences | `if constexpr` selects a branch at compile time in templated or constant-expression code. The discarded branch is not instantiated, which avoids invalid code paths for some types. It is useful for writing cleaner template logic. |

## 72. What are type traits?

| Field | Content |
|---|---|
| Question | What are type traits? |
| Answer Keyword | Compile-time type information |
| Answer Sentences | Type traits are templates that provide information or transformations about types at compile time. Examples include `std::is_integral`, `std::remove_reference`, and `std::is_same`. They are useful in generic programming and constraints. |

---

# Exceptions, Error Handling, and Safety

## 73. What is exception safety?

| Field | Content |
|---|---|
| Question | What is exception safety? |
| Answer Keyword | Correct behavior when exceptions occur |
| Answer Sentences | Exception safety means code maintains valid state and does not leak resources when an exception is thrown. RAII is the main tool because destructors clean up automatically. I think about whether an operation provides the basic guarantee, strong guarantee, or no-throw guarantee. |

| Guarantee | Meaning |
|---|---|
| Basic | Object remains valid, no leaks |
| Strong | Operation succeeds or has no effect |
| No-throw | Operation does not throw |

## 74. When should you throw exceptions?

| Field | Content |
|---|---|
| Question | When should you throw exceptions? |
| Answer Keyword | Exceptional failure, cannot continue locally |
| Answer Sentences | I throw exceptions when an operation cannot complete and the local code cannot reasonably handle the failure. Exceptions work well for construction failure and higher-level error propagation. For expected control-flow results, I may prefer `std::optional`, `std::variant`, or an error-code style depending on the project. |

## 75. Why should destructors not throw?

| Field | Content |
|---|---|
| Question | Why should destructors not throw? |
| Answer Keyword | Exception during unwinding can terminate |
| Answer Sentences | Destructors should not throw because they may run while another exception is already being unwound. If a destructor throws during stack unwinding, the program can call `std::terminate`. Cleanup code should handle or log failures internally when possible. |

## 76. What is `noexcept`?

| Field | Content |
|---|---|
| Question | What is `noexcept`? |
| Answer Keyword | Function promises not to throw |
| Answer Sentences | `noexcept` declares that a function is not expected to throw. It helps optimization and affects library behavior, for example containers prefer moving elements when the move constructor is `noexcept`. I use it when I can honestly guarantee the function will not throw. |

## 77. What is the difference between assertion and exception?

| Field | Content |
|---|---|
| Question | What is the difference between assertion and exception? |
| Answer Keyword | Programmer bug vs runtime failure |
| Answer Sentences | An assertion checks a condition that should always be true if the program is correct. An exception reports a runtime failure that can happen even in correct code. I use assertions for internal invariants and exceptions or error results for recoverable failures. |

---

# Memory Layout, Performance, and Low-Level C++

## 78. What is alignment?

| Field | Content |
|---|---|
| Question | What is alignment? |
| Answer Keyword | Address multiple required by type |
| Answer Sentences | Alignment is the requirement that an object of a type must be placed at an address with a certain boundary. Proper alignment helps the CPU access data efficiently and sometimes is required for correctness. Struct padding often exists to satisfy alignment requirements. |

## 79. What is padding in a struct?

| Field | Content |
|---|---|
| Question | What is padding in a struct? |
| Answer Keyword | Extra bytes for alignment |
| Answer Sentences | Padding is unused space inserted by the compiler between members or at the end of a struct to satisfy alignment. Member ordering can affect total size. I do not rely on binary layout unless the type is explicitly designed and checked for that purpose. |

## 80. What is cache locality?

| Field | Content |
|---|---|
| Question | What is cache locality? |
| Answer Keyword | Nearby data is faster |
| Answer Sentences | Cache locality means programs run faster when they access memory that is close together and reused often. Contiguous containers like `std::vector` often perform better than pointer-heavy structures because the CPU can prefetch data. In performance-sensitive C++, memory access patterns can matter more than algorithmic constants. |

## 81. How do you avoid unnecessary copies?

| Field | Content |
|---|---|
| Question | How do you avoid unnecessary copies? |
| Answer Keyword | References, move, views, reserve |
| Answer Sentences | I avoid unnecessary copies by passing large read-only objects as `const&` or views, moving from objects when ownership is transferred, and reserving container capacity when the size is known. I also rely on return value optimization instead of overusing output parameters. The key is to keep ownership and lifetime clear. |

## 82. What is copy elision?

| Field | Content |
|---|---|
| Question | What is copy elision? |
| Answer Keyword | Construct directly in destination |
| Answer Sentences | Copy elision is an optimization where the compiler removes a copy or move by constructing the object directly in its final location. Since C++17, some forms are guaranteed. This makes returning objects by value efficient and idiomatic. |

## 83. What is profiling and why is it important?

| Field | Content |
|---|---|
| Question | What is profiling and why is it important? |
| Answer Keyword | Measure before optimizing |
| Answer Sentences | Profiling means measuring where a program spends time or allocates memory. It is important because intuition about performance is often wrong. I prefer to profile first, then optimize the real bottleneck while keeping correctness and readability. |

## 84. What is the difference between latency and throughput?

| Field | Content |
|---|---|
| Question | What is the difference between latency and throughput? |
| Answer Keyword | Time per operation vs operations per time |
| Answer Sentences | Latency is how long one operation takes from start to finish. Throughput is how many operations can be completed per unit of time. In C++ performance work, the best design depends on whether the system cares more about response time, total processing rate, or both. |

## 85. What is memory fragmentation?

| Field | Content |
|---|---|
| Question | What is memory fragmentation? |
| Answer Keyword | Free memory split into pieces |
| Answer Sentences | Memory fragmentation happens when free memory is divided into small blocks that are hard to reuse efficiently. It can increase allocation cost and memory usage. In C++, I reduce fragmentation by avoiding excessive small heap allocations, using containers carefully, and considering custom allocators only when measurement justifies it. |

## 86. What is placement new?

| Field | Content |
|---|---|
| Question | What is placement new? |
| Answer Keyword | Construct object in existing storage |
| Answer Sentences | Placement new constructs an object at a specific memory address that has already been allocated. It is a low-level tool used in allocators, memory pools, and some embedded or performance-sensitive code. It requires careful lifetime management because destruction must be called explicitly. |

---

# Concurrency and Thread Safety

## 87. What is a data race?

| Field | Content |
|---|---|
| Question | What is a data race? |
| Answer Keyword | Unsynchronized conflicting access |
| Answer Sentences | A data race occurs when two threads access the same memory at the same time, at least one access writes, and there is no proper synchronization. In C++, a data race is undefined behavior. I prevent it with mutexes, atomics, thread confinement, or message passing. |

## 88. What is the difference between concurrency and parallelism?

| Field | Content |
|---|---|
| Question | What is the difference between concurrency and parallelism? |
| Answer Keyword | Structure vs simultaneous execution |
| Answer Sentences | Concurrency is about structuring a program to handle multiple tasks that can overlap. Parallelism means tasks actually execute at the same time on multiple cores. A concurrent design may or may not run in parallel, depending on the system and scheduler. |

## 89. What is `std::thread`?

| Field | Content |
|---|---|
| Question | What is `std::thread`? |
| Answer Keyword | Owns a thread of execution |
| Answer Sentences | `std::thread` represents a thread of execution. After starting it, I must either `join()` it or `detach()` it before the `std::thread` object is destroyed, otherwise the program terminates. In modern C++, `std::jthread` is often safer because it joins automatically. |

## 90. What is `std::jthread`?

| Field | Content |
|---|---|
| Question | What is `std::jthread`? |
| Answer Keyword | RAII thread with stop support |
| Answer Sentences | `std::jthread` is a C++20 thread wrapper that joins automatically in its destructor. It can also work with stop tokens for cooperative cancellation. I prefer it over `std::thread` when C++20 is available and automatic joining matches the design. |

| Tool | Join Behavior | Cancellation |
|---|---|---|
| `std::thread` | Manual `join()` or `detach()` | No built-in stop token |
| `std::jthread` | Auto-joins in destructor | Supports cooperative stop |
| `std::async` | Higher-level async task | Future-based result |

## 91. What is a mutex?

| Field | Content |
|---|---|
| Question | What is a mutex? |
| Answer Keyword | Mutual exclusion |
| Answer Sentences | A mutex protects shared data by allowing only one thread to enter a critical section at a time. In C++, I usually manage mutex locking with RAII wrappers like `std::lock_guard` or `std::unique_lock`. The protected data and locking rule should be clear in the design. |

## 92. What is the difference between `std::lock_guard` and `std::unique_lock`?

| Field | Content |
|---|---|
| Question | What is the difference between `std::lock_guard` and `std::unique_lock`? |
| Answer Keyword | Simple RAII lock vs flexible lock |
| Answer Sentences | `std::lock_guard` is a simple RAII lock that locks on construction and unlocks on destruction. `std::unique_lock` is more flexible: it can defer locking, unlock and relock, and is required for condition variables. I use `lock_guard` by default and `unique_lock` when I need the extra behavior. |

## 93. What is a condition variable?

| Field | Content |
|---|---|
| Question | What is a condition variable? |
| Answer Keyword | Wait for shared state change |
| Answer Sentences | A condition variable lets a thread sleep until another thread notifies it that shared state may have changed. It must be used with a mutex and a predicate because wakeups can be spurious. The correct pattern is to wait in a predicate-based loop. |

## 94. What is an atomic variable?

| Field | Content |
|---|---|
| Question | What is an atomic variable? |
| Answer Keyword | Thread-safe single object operation |
| Answer Sentences | An atomic variable supports operations that are safe from data races without using a mutex for that object. Atomics are good for simple counters, flags, and low-level synchronization. They are not a replacement for mutexes when multiple values must change together as one invariant. |

## 95. What is deadlock?

| Field | Content |
|---|---|
| Question | What is deadlock? |
| Answer Keyword | Threads wait forever |
| Answer Sentences | Deadlock happens when threads wait on each other in a cycle and none can continue. A common cause is taking multiple locks in inconsistent order. I prevent it by using a fixed lock order, minimizing lock scope, and using helpers like `std::scoped_lock` for multiple mutexes. |

## 96. What is false sharing?

| Field | Content |
|---|---|
| Question | What is false sharing? |
| Answer Keyword | Independent data shares cache line |
| Answer Sentences | False sharing occurs when different threads modify different variables that happen to sit on the same cache line. The variables are logically independent, but the CPU cache coherence traffic makes performance poor. It is a performance issue found through measurement, not a correctness bug. |

## 97. What is memory ordering in atomics?

| Field | Content |
|---|---|
| Question | What is memory ordering in atomics? |
| Answer Keyword | Visibility and ordering guarantees |
| Answer Sentences | Memory ordering controls what visibility and ordering guarantees atomic operations provide between threads. The default `std::memory_order_seq_cst` is the strongest and easiest to reason about. I only use weaker ordering when there is a measured need and the synchronization design is carefully reviewed. |

---

# API Design and Production C++ Judgment

## 98. How do you decide whether to pass by value, reference, or pointer?

| Field | Content |
|---|---|
| Question | How do you decide whether to pass by value, reference, or pointer? |
| Answer Keyword | Small copy, required reference, optional pointer |
| Answer Sentences | I pass small cheap types by value. I pass large read-only objects by `const&` or a view type. I use non-const references for required output or modification, and pointers when null is meaningful or the API needs pointer semantics. |

## 99. When should a function return by value?

| Field | Content |
|---|---|
| Question | When should a function return by value? |
| Answer Keyword | Clear ownership and RVO |
| Answer Sentences | Returning by value is good when the function creates and returns a new object. Modern C++ makes this efficient through move semantics and copy elision. It also gives clear ownership to the caller and avoids lifetime problems from returning references. |

## 100. When is returning a reference dangerous?

| Field | Content |
|---|---|
| Question | When is returning a reference dangerous? |
| Answer Keyword | Lifetime may not outlive caller |
| Answer Sentences | Returning a reference is dangerous if the referred object does not outlive the caller. Returning a reference to a local variable is always wrong. I only return references when the lifetime is clearly tied to an existing object, such as a member access function. |

## 101. What makes a good C++ API?

| Field | Content |
|---|---|
| Question | What makes a good C++ API? |
| Answer Keyword | Clear ownership, invariants, errors |
| Answer Sentences | A good C++ API makes ownership, lifetime, mutability, and error behavior clear. It should be hard to misuse and should express intent through types. I prefer APIs that use RAII, standard library types, and narrow responsibilities. |

## 102. How do you design a class invariant?

| Field | Content |
|---|---|
| Question | How do you design a class invariant? |
| Answer Keyword | Always valid after construction |
| Answer Sentences | A class invariant is a condition that should be true for every observable valid state of the object. Constructors establish it, member functions preserve it, and destructors clean up. I design classes so invalid states are difficult or impossible to represent. |

## 103. Why prefer composition over inheritance?

| Field | Content |
|---|---|
| Question | Why prefer composition over inheritance? |
| Answer Keyword | Lower coupling, clearer ownership |
| Answer Sentences | Composition often creates lower coupling because a class owns or uses another object instead of becoming a subtype. It is easier to change internals without affecting users. I still use inheritance when polymorphism or a real is-a relationship is the right model. |

## 104. How do you handle errors in modern C++?

| Field | Content |
|---|---|
| Question | How do you handle errors in modern C++? |
| Answer Keyword | Exceptions, optional, variant, error codes |
| Answer Sentences | I choose error handling based on the kind of failure. For exceptional failures, exceptions can keep normal code clean. For expected absence, `std::optional` is clear. For multiple result types or error states, `std::variant` or a project-specific result type can be better. |

| Tool | Best For |
|---|---|
| Exception | Cannot complete operation normally |
| `std::optional` | Value may be absent |
| `std::variant` | One of several typed outcomes |
| Error code | Low-level or no-exception boundaries |

## 105. How do you review C++ code for safety?

| Field | Content |
|---|---|
| Question | How do you review C++ code for safety? |
| Answer Keyword | Lifetime, ownership, bounds, concurrency |
| Answer Sentences | I first look for lifetime and ownership problems, such as dangling references or unclear raw pointers. Then I check bounds, error handling, exception safety, and thread synchronization. I also look for whether standard library tools could replace manual resource management. |

## 106. How do you make C++ code easier to test?

| Field | Content |
|---|---|
| Question | How do you make C++ code easier to test? |
| Answer Keyword | Small units, interfaces, deterministic behavior |
| Answer Sentences | I make C++ code easier to test by keeping functions focused, separating pure logic from side effects, and injecting dependencies where needed. Deterministic code is much easier to unit test. For classes, clear invariants and small public APIs help tests stay meaningful. |

## 107. What is the difference between `std::optional`, `std::variant`, and a pointer for optional results?

| Field | Content |
|---|---|
| Question | What is the difference between `std::optional`, `std::variant`, and a pointer for optional results? |
| Answer Keyword | Maybe value, typed alternatives, object address |
| Answer Sentences | `std::optional<T>` is best when the result is either a `T` or absent. `std::variant` is better when there are several meaningful typed outcomes. A pointer is better when the result refers to an existing object or null has pointer-specific meaning. |

| Choice | Owns Value? | Meaning |
|---|---|---|
| `std::optional<T>` | Yes | Maybe a value |
| `std::variant<A, B>` | Yes | One of several alternatives |
| `T*` | No, unless documented otherwise | Nullable reference/address |

## 108. How would you explain move semantics in a real project?

| Field | Content |
|---|---|
| Question | How would you explain move semantics in a real project? |
| Answer Keyword | Transfer expensive resources cheaply |
| Answer Sentences | Move semantics let objects transfer resources instead of copying them. For example, moving a vector can transfer its internal buffer instead of copying every element. In a real project, this improves performance while preserving clear ownership, but I only move from objects I no longer need. |

## 109. How do you avoid lifetime bugs with callbacks or lambdas?

| Field | Content |
|---|---|
| Question | How do you avoid lifetime bugs with callbacks or lambdas? |
| Answer Keyword | Capture intentionally; avoid dangling `this` |
| Answer Sentences | I avoid lifetime bugs by being explicit about what a callback captures and how long it can live. Capturing `this` is dangerous if the callback can run after the object is destroyed. For asynchronous code, I use ownership-aware captures such as `std::weak_ptr` when appropriate. |

## 110. What is your general strategy for writing high-quality C++?

| Field | Content |
|---|---|
| Question | What is your general strategy for writing high-quality C++? |
| Answer Keyword | RAII, clear ownership, standard tools, tests |
| Answer Sentences | My strategy is to make ownership and lifetime explicit, use RAII and standard library types, keep interfaces small, and avoid undefined behavior. I prefer simple designs that are easy to test and profile. When performance matters, I measure first and optimize the real bottleneck without sacrificing correctness. |

