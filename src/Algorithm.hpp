#ifndef ALGORITHM_HPP
#define ALGORITHM_HPP

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

class Algorithm{
public:
    virtual ~Algorithm() = default;
    virtual void compute_algorithm() = 0;
    pybind11::dict get_resulting_data() const;

protected:
    pybind11::dict m_output_data;
};

#endif
