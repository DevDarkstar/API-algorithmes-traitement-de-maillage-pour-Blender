#ifndef ROUTER_HPP
#define ROUTER_HPP

#include "Algorithm.hpp"
#include <vector>
#include <map>
#include <functional>

class Router{
public:
    Router(int id, std::string algorithm_name, pybind11::dict data);
    ~Router();
    void init();
    pybind11::dict get_result();

private:
    static std::vector<std::map<std::string, std::function<Algorithm*(const pybind11::dict&)>>> algorithms_table;
    Algorithm* m_current_algorithm;
};

#endif
