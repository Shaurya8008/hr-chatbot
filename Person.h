#ifndef PERSON_H
#define PERSON_H

#include <string>
#include <iostream>

/**
 * ABSTRACTION: This is an abstract base class.
 * It defines the interface that all Persons must follow but cannot be instantiated.
 */
class Person {
protected: 
    // ENCAPSULATION: Members are protected so derived classes can use them,
    // but external code cannot access them directly.
    std::string name;
    std::string email;

public:
    Person(std::string n, std::string e) : name(n), email(e) {}
    virtual ~Person() {} // Virtual destructor for safe polymorphic deletion

    // Setters and Getters (Encapsulation)
    std::string getName() const { return name; }
    void setName(std::string n) { name = n; }
    
    std::string getEmail() const { return email; }

    /**
     * POLYMORPHISM: Declare a virtual function.
     * Making it = 0 makes this class Abstract.
     */
    virtual void displayInfo() = 0; 
};

#endif
