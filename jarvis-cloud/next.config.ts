import type { NextConfig } from "next";

/**
 * Configuration Next.js — mode export statique pour hébergement Hostinger.
 *
 * En production on génère un dossier `out/` avec des fichiers statiques
 * (HTML/JS/CSS) que l'on dépose sur le sous-domaine
 * https://jarvis.creatorsystemia.fr.
 *
 * Pas de Node.js requis côté serveur : Hostinger sert juste les fichiers.
 */
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // Génère /app/index.html (au lieu de /app.html) pour que les
  // hébergeurs classiques résolvent /app -> /app/index.html.
};

export default nextConfig;
