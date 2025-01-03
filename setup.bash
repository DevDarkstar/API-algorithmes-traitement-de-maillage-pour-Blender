#!/bin/bash

# Chemin absolu du dossier dans lequel est exécuté le script courant
SCRIPT_DIR=$(dirname "$(realpath "$0")")
# URL menant à l"archive CGAL à télécharger
URL="https://github.com/CGAL/cgal/releases/download/v5.6.1/CGAL-5.6.1.tar.xz"
# Nom de l'archive CGAL
FILE="CGAL-5.6.1"
# Extension de l'archive CGAL
EXTENSION=".tar.xz"
# Nom du dossier contenant CGAL (pour vérifier si CGAL est déjà installé)
DIR_LOCATION="libraries/CGAL-5.6.1"

# Nous vérifions si CGAL n'est pas déjà installé
if [[ ! -d "$DIR_LOCATION" ]]; then

    echo "Téléchargement de l'archive CGAL 5.6.1..."

    # Téléchargement de l'archive CGAL dans le répertoire où le script est situé
    wget -O "$SCRIPT_DIR/$FILE$EXTENSION" "$URL"

    # Nous vérifions si nous avons bien pu télécharger l'archive
    if [[ $? -ne 0 ]]; then
        echo "Échec du téléchargement de $FILE$EXTENSION."
        exit 1
    fi

    # Décompression de l'archive
    tar -xf "$FILE$EXTENSION"

    # Vérification de la décompression de l'archive contenant CGAL
    if [[ $? -ne 0 ]]; then
        echo "Échec de la décompression de l'archive $FILE$EXTENSION."
        exit 1
    fi

    # Déplacement de l'archive CGAL téléchargée dans le dossier "libraries"
    mv $FILE libraries/

    # Vérification si l'archive a bien été déplacée
    if [[ ! -d "$DIR_LOCATION" ]]; then
        echo "Echec lors du déplacement de $FILE vers le dossier libraries"
        exit 1
    fi

    echo "Téléchargement de l'archive CGAL réussie"

# Sinon CGAL est déjà été téléchargé
else
    echo "$FILE a déjà été téléchargé..."
fi

# Nom du dossier contenant les fichiers de compilation
BUILD_DIR="build"
# Dossier contenant l'extension Blender
EXTENSION_DIR="api_traitements_maillage"
# Dossier du package Python contenant l'ensemble des modules de l'extension
MODULE_DIR="api_modules"

echo "Compilation du programme..."

# Création du dossier "build" si non présent afin d'y stocker tous les fichiers de compilation
if [[ ! -d "$BUILD_DIR" ]]; then
    mkdir "$BUILD_DIR"
fi

# Se rendre dans le dossier "build"
cd "$BUILD_DIR" || exit

# Exécution du cmake
cmake -DCGAL_DIR=$SCRIPT_DIR/$DIR_LOCATION -DCMAKE_BUILD_TYPE=Release ..

# Vérification si le cmake s'est bien exécuté
if [[ $? -ne 0 ]]; then
    echo "Erreur lors de l'exécution du cmake"
    exit 1
fi

# Compilation du programme
make

# Déplacement du fichier compilé dans le dossier "api_modules', servant de package pour les modules Python de l'extension
mv *.so ../$EXTENSION_DIR/$MODULE_DIR

# Vérification si le fichier a bien été déplacé dans le dossier de l'extension
if [[ $? -ne 0 ]]; then
    echo "Erreur lors du déplacement du fichier .so dans le dossier $MODULE_DIR. Vérifiez que ce dernier existe bien..."
    exit 1
fi

cd ../$EXTENSION_DIR

# Enfin, compression au format .zip du dossier contenant les fichiers de l'extension Blender
zip -r api_traitement_maillage.zip ./*

echo "Création de l'extension Blender réussie dans le dossier '$EXTENSION_DIR'."
