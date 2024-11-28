#include "Algorithm.hpp"

pybind11::dict Algorithm::get_resulting_data() const {
    return this->m_output_data;
}
