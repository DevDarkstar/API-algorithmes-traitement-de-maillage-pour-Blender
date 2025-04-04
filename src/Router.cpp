#include "Router.hpp"
#include "SurfaceMeshSimplification.hpp"
#include "SurfaceMeshSegmentation.hpp"
#include "SurfaceAreaComputation.hpp"
#include <stdexcept>
#include <iostream>
#include "TestCpp.hpp"

namespace py = pybind11;

std::map<std::string, std::function<std::unique_ptr<Algorithm>(const pybind11::dict&)>> Router::algorithms_table = 
                                                            {
                                                                {
                                                                    {"segmentation_cgal", [](const py::dict& data){ return std::make_unique<SurfaceMeshSegmentation>(data); }},
                                                                    {"simplification_cgal", [](const py::dict& data){ return std::make_unique<SurfaceMeshSimplification>(data); }},
                                                                    {"area_computation_cgal", [](const py::dict& data){ return std::make_unique<SurfaceAreaComputation>(data); }},
                                                                    {"test_cpp", [](const py::dict& data){ return std::make_unique<TestCpp>(data); }}
                                                                }
                                                            };


Router::Router(std::string algorithm_name, py::dict data): m_current_algorithm(algorithms_table[algorithm_name](data))
{}

Router::~Router()
{
    //delete m_current_algorithm;
    // débogage
    //std::cout << "La mémoire allouée au router a bien été liberée" << std::endl;
}

void Router::init()
{
    try{
        this->m_current_algorithm->compute_algorithm();
    }catch(const std::exception& e){
        std::cerr << "Une erreur s'est produite lors de l'exécution d'un algorithme de l'API C++ : " << e.what() << std::endl;
        throw;
    }
}

py::dict Router::get_result()
{
    return this->m_current_algorithm->get_resulting_data();
}

PYBIND11_MODULE(algorithms_api, handle){
    handle.doc() = "Classe implémentant divers algorithmes CGAL permettant d'effectuer des taritements sur des maillages";

    py::class_<Router>(handle, "Router")
        .def(py::init<std::string, py::dict>())
        .def("init", &Router::init)
        .def("get_result", &Router::get_result);
}
