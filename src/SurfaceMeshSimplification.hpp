#ifndef SURFACEMESHSIMPLIFICATION_HPP
#define SURFACEMESHSIMPLIFICATION_HPP

#include "Algorithm.hpp"
#include <map>

#include <CGAL/Simple_cartesian.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Surface_mesh_simplification/edge_collapse.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Edge_count_ratio_stop_predicate.h>
#include <CGAL/boost/graph/generators.h>

namespace simplification {
    typedef CGAL::Simple_cartesian<double>          Kernel;
    typedef Kernel::Point_3                         Point_3;
    typedef CGAL::Surface_mesh<Point_3>             Surface_mesh;
    typedef Surface_mesh::Vertex_index              vertex_descriptor;
    typedef Surface_mesh::Face_index                face_descriptor;
}

class SurfaceMeshSimplification : public Algorithm{
public:
    explicit SurfaceMeshSimplification(const pybind11::dict& data);
    void compute_algorithm() override;
    void update_vertex_coordinates();
    void update_face_indices(std::map<simplification::vertex_descriptor, int>& vertex_reindexing);
    std::map<simplification::vertex_descriptor, int> get_vertex_reindexing();

private:
    simplification::Surface_mesh m_surface_mesh;
    double m_stop_ratio;
};

#endif
