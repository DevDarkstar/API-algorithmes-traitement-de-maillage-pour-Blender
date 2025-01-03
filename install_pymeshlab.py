import bpy
import os
import sys
import subprocess

# Nous vérifions que le ou les modules nécessaires sont bien installés
# récupération du chemin absolu vers les modules tiers installés dans Blender
modules_path = bpy.utils.user_resource("SCRIPTS", path="modules")

# Si un des modules est manquant
if not os.path.isdir(os.path.join(modules_path, "pymeshlab")):
    # mise à niveau de pip
    subprocess.run([sys.executable, "-m", "ensurepip"])
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    # Nous vérifions s'il est bien installé dans l'environnement python de Blender
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "pymeshlab", "-t", modules_path])
    print("Installation des modules requis terminée. Merci de redémarrer Blender pour appliquer les changements...")
# Sinon le module est déjà installé
else:
    print("Les modules requis sont déjà installés.")
