#ifndef MESHLAB_HPP
#define MESHLAB_HPP

#include "Algorithm.hpp"

class MeshLab : public Algorithm{
public:
    explicit MeshLab(const pybind11::dict& data);
    void compute_algorithm() override;

private:
    pybind11::dict m_input_data;
    std::string m_function_name;
};

#endif