#include "TestCpp.hpp"

namespace py = pybind11;

TestCpp::TestCpp(const py::dict& data) {
    //Toutes les données, provenant de notre structure de données python, sont castées vers leurs types C++ idoines
    this->m_output_option = data["options"]["output_option"].cast<std::string>();
}

void TestCpp::compute_algorithm(){
    if(m_output_option == "DISPLAY_TEXT") {
        this->m_output_data["output_result"] = std::array<std::string,1>{"message"};
        this->m_output_data["result_infos"] = "Ceci est un message provenant d'un algorithme C++ pur.";
    }else {
        this->m_output_data["output_result"] = std::array<std::string,1>{"add_mesh"};
        // Coordonnées des sommets de la pyramide
        //v1 = {0.0,0.0,0.0}
        //v2 = {1.0,0.0,0.0}
        //v3 = {0.5,1.0,0.0}
        //v4 = {0.5,0.5,1.0}
        this->m_output_data["vertices"] = std::array<double, 12>{0.0,0.0,0.0,1.0,0.0,0.0,0.5,1.0,0.0,0.5,0.5,1.0};
        this->m_output_data["faces"] = std::array<int, 12>{0,1,2,3,1,2,3,0,2,0,1,3};
    }
}
