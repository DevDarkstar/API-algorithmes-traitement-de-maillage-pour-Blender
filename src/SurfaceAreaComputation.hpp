#ifndef SURFACEAREACOMPUTATION_HPP
#define SURFACEAREACOMPUTATION_HPP

#include "Algorithm.hpp"

#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <vector>

namespace cgal_area_computation{
    typedef CGAL::Exact_predicates_inexact_constructions_kernel      Kernel;
    typedef Kernel::Point_3                                          Point_3;
    typedef Kernel::Vector_3                                         Vector_3;
}

class SurfaceAreaComputation : public Algorithm{
public:
    explicit SurfaceAreaComputation(const pybind11::dict& data);
    void compute_algorithm() override;

private:
    std::vector<std::array<cgal_area_computation::Point_3, 3>> m_faces;
    std::string m_output_option;
};

#endif
