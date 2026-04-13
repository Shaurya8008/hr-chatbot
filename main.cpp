#include <iostream>
#include <vector>
#include <memory>
#include "Person.h"
#include "Candidate.h"
#include "Employee.h"

// Abstraction: Interface for System Management
class IHRManager {
public:
    virtual void registerPerson(std::shared_ptr<Person> p) = 0;
    virtual void showAllRecords() = 0;
    virtual ~IHRManager() {}
};

// Encapsulation: Managing person records within a class
class HRSystem : public IHRManager {
private:
    std::vector<std::shared_ptr<Person>> people;

public:
    void registerPerson(std::shared_ptr<Person> p) override {
        people.push_back(p);
    }

    void showAllRecords() override {
        std::cout << "\n--- HR SYSTEM DATABASE ---\n" << std::endl;
        for (const auto& p : people) {
            // Polymorphism in action: Correct displayInfo() called at runtime
            p->displayInfo();
            std::cout << "--------------------------" << std::endl;
        }
    }
};

int main() {
    HRSystem system;

    // Creating objects using Polymorphism (Base class pointers)
    auto c1 = std::make_shared<Candidate>("Alice Smith", "alice@example.com", 101);
    c1->addSkill("C++");
    c1->addSkill("OOP");
    c1->addSkill("SQL");

    auto e1 = std::make_shared<Employee>("Bob Wilson", "bob.hr@company.com", "Engineering", 75000.0);
    auto c2 = std::make_shared<Candidate>("Charlie Brown", "charlie@gmail.com", 102);
    c2->addSkill("Python");

    // Registering different types through the common interface
    system.registerPerson(c1);
    system.registerPerson(e1);
    system.registerPerson(c2);

    // Displaying all records polymorphically
    system.showAllRecords();

    return 0;
}
