#include "MeshLab.hpp"
#include <boost/format.hpp>
#include <pybind11/embed.h>
#include <iostream>

namespace py = pybind11;

MeshLab::MeshLab(const py::dict& data) : m_input_data(data){
    this->m_function_name = data["function"].cast<std::string>();
}

void MeshLab::compute_algorithm(){
    std::cout << "hello\n"; 
    try{    
        py::scoped_interpreter guard{};
        std::cout << "hello2" << std::endl;
        // Charger le module Python
        py::object my_script = py::module_::import("my_script");
        // Créer un dictionnaire en C++
        py::dict params;
        params["key1"] = 42;
        params["key2"] = "valeur";

        // Appeler la fonction Python avec un dictionnaire comme paramètre
        py::object result = my_script.attr("get_data")();

        std::cout << "Résultat: " << py::str(result).cast<std::string>() << std::endl;
    } catch (const py::error_already_set& e) {
        std::cerr << "Erreur Python: " << e.what() << std::endl;
    }

    // Création du message de résultat
    boost::format message = boost::format("Nombre de la fonction utilisée : %1%.") 
                            % this->m_function_name;
    this->m_output_data["result_infos"] = message.str();
    this->m_output_data["output_result"] = "message";
}
