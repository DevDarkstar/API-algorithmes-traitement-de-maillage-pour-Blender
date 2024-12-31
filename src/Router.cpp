#include "Router.hpp"
#include "SurfaceMeshSimplification.hpp"
#include "SurfaceMeshSegmentation.hpp"
#include "SurfaceAreaComputation.hpp"
#include "TestCpp.hpp"
#include "MeshLab.hpp"
//#include <iostream>

namespace py = pybind11;

std::vector<std::map<std::string, std::function<Algorithm*(const pybind11::dict&)>>> Router::algorithms_table = 
                                                            {
                                                                {
                                                                    {"segmentation_cgal", [](const py::dict& data){ return new SurfaceMeshSegmentation(data); }},
                                                                    {"simplification_cgal", [](const py::dict& data){ return new SurfaceMeshSimplification(data); }},
                                                                    {"area_computation_cgal", [](const py::dict& data){ return new SurfaceAreaComputation(data); }},
                                                                    {"test_cpp", [](const py::dict& data){ return new TestCpp(data); }}
                                                                },{
                                                                    {"colorize_curvature_apss", [](const py::dict& data){ return new MeshLab(data); }}
                                                                }
                                                            };


Router::Router(int id, std::string algorithm_name, py::dict data): m_current_algorithm(algorithms_table[id][algorithm_name](data))
{}

Router::~Router()
{
    delete m_current_algorithm;
    // débogage
    //std::cout << "La mémoire allouée au router a bien été liberée" << std::endl;
}

void Router::init()
{
    this->m_current_algorithm->compute_algorithm();
}

py::dict Router::get_result()
{
    return this->m_current_algorithm->get_resulting_data();
}

PYBIND11_MODULE(algorithms_api, handle){
    handle.doc() = "Classe implémentant divers algorithmes CGAL permettant d'effectuer des taritements sur des maillages";

    py::class_<Router>(handle, "Router")
        .def(py::init<int, std::string, py::dict>())
        .def("init", &Router::init)
        .def("get_result", &Router::get_result);
}
