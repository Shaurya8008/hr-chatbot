#ifndef CANDIDATE_H
#define CANDIDATE_H

#include "Person.h"
#include <vector>

/**
 * INHERITANCE: Candidate IS-A Person.
 * Inherits name and email from Person.
 */
class Candidate : public Person {
private:
    std::vector<std::string> skills;
    int applicationID;

public:
    Candidate(std::string n, std::string e, int id) 
        : Person(n, e), applicationID(id) {}

    void addSkill(std::string skill) { 
        skills.push_back(skill); 
    }

    /**
     * POLYMORPHISM: Implementation of the virtual function.
     * Each derived class provides its own specific implementation.
     */
    void displayInfo() override {
        std::cout << "[Candidate] ID: " << applicationID 
                  << " | Name: " << name 
                  << " | Email: " << email << std::endl;
        std::cout << "   Skills matched: ";
        for(size_t i = 0; i < skills.size(); ++i) {
            std::cout << skills[i] << (i == skills.size()-1 ? "" : ", ");
        }
        std::cout << std::endl;
    }
};

#endif
