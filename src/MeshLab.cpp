#include "MeshLab.hpp"
#include <boost/format.hpp>

namespace py = pybind11;

MeshLab::MeshLab(const py::dict& data) : m_input_data(data){
    this->m_function_name = data["function"].cast<std::string>();
}

void MeshLab::compute_algorithm(){

    // Création du message de résultat
    boost::format message = boost::format("Nombre de la fonction utilisée : %1%.") 
                            % this->m_function_name;
    this->m_output_data["result_infos"] = message.str();
    this->m_output_data["output_result"] = "message";
}
