#ifndef EMPLOYEE_H
#define EMPLOYEE_H

#include "Person.h"
#include <iomanip>

/**
 * INHERITANCE: Employee IS-A Person.
 */
class Employee : public Person {
private:
    std::string department;
    double salary;

public:
    Employee(std::string n, std::string e, std::string dept, double sal) 
        : Person(n, e), department(dept), salary(sal) {}

    /**
     * POLYMORPHISM: Specific implementation for Employee.
     */
    void displayInfo() override {
        std::cout << "[Employee] Name: " << name 
                  << " | Dept: " << department 
                  << " | Email: " << email << std::endl;
        std::cout << "   Monthly Salary: $" << std::fixed << std::setprecision(2) << salary << std::endl;
    }
};

#endif
