#ifndef TESTCPP_HPP
#define TESTCPP_HPP

#include "Algorithm.hpp"

class TestCpp : public Algorithm{
public:
    explicit TestCpp(const pybind11::dict& data);
    void compute_algorithm() override;

private:
    std::string m_output_option;
};

#endif
