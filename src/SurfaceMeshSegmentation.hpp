#ifndef SURFACEMESHSEGMENTATION_HPP
#define SURFACEMESHSEGMENTATION_HPP

#include "Algorithm.hpp"

#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/mesh_segmentation.h>
#include <CGAL/Polygon_mesh_processing/IO/polygon_mesh_io.h>
#include <CGAL/property_map.h>

namespace segmentation{
    typedef CGAL::Exact_predicates_inexact_constructions_kernel      Kernel;
    typedef Kernel::Point_3                                          Point_3;
    typedef CGAL::Surface_mesh<Point_3>                              Surface_mesh;
    typedef boost::graph_traits<Surface_mesh>::vertex_descriptor     vertex_descriptor;
    typedef boost::graph_traits<Surface_mesh>::face_descriptor       face_descriptor;
    typedef Surface_mesh::Property_map<face_descriptor,double>       Facet_double_map;
    typedef Surface_mesh::Property_map<face_descriptor, std::size_t> Facet_int_map;
}

class SurfaceMeshSegmentation : public Algorithm{
public:
    explicit SurfaceMeshSegmentation(const pybind11::dict& data);
    void compute_algorithm() override;
    void update_segments_ids();

private:
    segmentation::Surface_mesh m_surface_mesh;
    int m_clusters;
    double m_smoothness;
    std::string m_output_option;
};

#endif
