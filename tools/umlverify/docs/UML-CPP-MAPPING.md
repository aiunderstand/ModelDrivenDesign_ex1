# UML ↔ C++ mapping contract

This is the single most important document in the repository. Two consumers must agree with it
exactly, or every report the tool produces is noise:

1. the Copilot prompt that implements a design (planned: `.github/prompts/implement-design.prompt.md`)
   — how the AI turns the design into C++
2. [`class_diagram/cpp_extract.py`](../class_diagram/cpp_extract.py) — how libclang turns that C++ back into the
   implemented design

If you change a rule here, change it in both, and re-run `tools/verify.py --all` to check the
examples still give the results their READMEs describe.

## Scope rules

- **The UML surface is headers only** — `impl/include/**/*.hpp`. Files under `impl/src/` are
  never read for diagram purposes.
- **Constructors, destructors and operator overloads are omitted** from diagrams.
- **A member that creates a relation is not also listed as an attribute.** Pick one: if
  `std::shared_ptr<Loan> loan_` becomes an aggregation edge, it does not also appear in the
  attribute compartment.
- **Primitives and standard value types are always attributes, never relations** — `int`,
  `double`, `bool`, `char`, `std::string`, `std::string_view`, and enums.
- Getters and setters are ordinary methods. They are not folded back into attributes.
- Trailing underscores on private members (`items_`) are stripped for the diagram (`items`).

## Visibility

| UML | C++ |
|---|---|
| `+` | `public:` |
| `#` | `protected:` |
| `-` | `private:` (the default for `class`) |
| `~` | not used in this project |

## Classifiers

| UML | C++ |
|---|---|
| `class` | `class` or `struct` with at least one data member |
| `<<abstract>>` | has at least one pure-virtual method (`= 0`) **and** at least one data member |
| `<<interface>>` | all methods pure virtual, **no** data members, has a virtual destructor |
| `<<enumeration>>` | `enum class` |
| generics | `template<typename T>` — rendered `Catalog~T~` |

An interface is therefore just an abstract class that carries no state. The distinction is made
mechanically, not by naming convention, so `IFoo` naming is neither required nor sufficient.

## Relations

Direction is always **from the owner to the owned/used type**.

| UML | C++ | Mermaid |
|---|---|---|
| inheritance | `class Derived : public Base` where `Base` has data members | `Base <|-- Derived` |
| realization | `class C : public I` where `I` is interface-shaped | `I <|.. C` |
| **composition** | `std::unique_ptr<T>` member, **or** a by-value `T` member | `Owner *-- T` |
| **aggregation** | `std::shared_ptr<T>` member | `Owner o-- T` |
| **association** | `T*`, `T&`, or `std::weak_ptr<T>` member | `Owner --> T` |
| dependency | `T` appears only in a parameter or return type — never as a member | `User ..> T` |

A dependency is only recorded when there is no stronger relation to the same type. Enums never
take part in relations.

Designers rarely draw a dependency arrow for every parameter type, so the verifier does not count
an implemented dependency as *extra* when the design already implies it through a method
signature. The report lists such arrows under **Not counted**.

Types used through a project template relate to the template: a `Catalog<Member>` member is a
relation to `Catalog`, not to `Member`. A template's own parameter (`T`) is never a relation.

The three ownership relations are the heart of the exercise. They are not stylistic: `unique_ptr`
means *this object's lifetime is mine*, `shared_ptr` means *shared, I am one of several owners*,
and a raw pointer means *I merely refer to it*. Getting these wrong is the most common and most
consequential error an AI makes when implementing a class diagram, and it compiles cleanly either
way.

## Multiplicity

A member says how many objects its class refers to, so it fixes the multiplicity at the **far
end** of the relation — the end of the class that is referred to:

| UML, far end | C++ |
|---|---|
| `1` | a single by-value, pointer or reference member |
| `0..1` | `std::optional<T>` |
| `*` | `std::vector<T>`, `std::map<K,T>`, `std::set<T>`, `std::list<T>` |

Multiplicity composes with ownership. `std::vector<std::unique_ptr<LibraryItem>>` is a
**composition with `*`**: `Library *-- "*" LibraryItem`. `std::vector<std::shared_ptr<Loan>>` is
an **aggregation with `*`**: `Library o-- "*" Loan`.

The **near end** ("how many `Loan`s point at one `Member`?") cannot be expressed by a member, so
the extractor never states it and the verifier does not compare it. A design may still show it —
for a composition the whole's end is `1` by definition, and `Loan --> Member` could honestly be
`*` to `1` — but it is documentation, not something the code can confirm.

## Drawing relations

How a relation is drawn, in draw.io and in the comparison:

- The **role name** is the member's name (`borrower_` → `borrower`) and the **multiplicity** is as
  above. Both go at the far end, on either side of the line, just outside the class.
- Every relation has an open **navigability arrowhead** at the far end, because a C++ member makes
  it one-way: the owner can reach the other class, not the reverse. Composition and aggregation
  keep their diamond at the owner's end as well.
- Inheritance and realization have a hollow triangle at the parent; dependency is dashed with an
  open arrowhead. None of these carry role names or multiplicities.

## Method and attribute modifiers

| UML | C++ |
|---|---|
| `$` (static) | `static` member |
| `*` (abstract) | pure virtual, `= 0` |
| `const` method | trailing `const` — recorded but not rendered in mermaid |
| `virtual` (non-pure) | recorded but not rendered |

## Type normalization

The diff normalizes types before comparing, so these are all equal:

| Written as | Normalizes to |
|---|---|
| `std::string`, `string` | `string` |
| `std::size_t`, `size_t`, `unsigned long` | `size_t` |
| `std::int32_t`, `int32_t`, `int` | `int` |
| `std::vector<T>`, `T[]` | `list<T>` |
| `std::unique_ptr<T>`, `std::shared_ptr<T>`, `T*`, `const T&` in a signature | `T` |
| `bool`, `boolean` | `bool` |
| `void` | `void` |

Names are matched case-insensitively with non-alphanumerics stripped, so `item_count`,
`itemCount` and `ItemCount` are the same member. This is deliberate: the exercise measures
*structure*, not naming style. A different word is a different name, though: `getItemCount` is
not `itemCount`.

## Worked reference

`examples/2-class-library/` implements every rule on this page. When in doubt, read
`examples/2-class-library/impl/include/library/` next to
`examples/2-class-library/diagrams/output/class-design.mmd`.
