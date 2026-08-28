// ============================================================
// CONFIGURATION SUPABASE
// ============================================================
// À COMPLÉTER une fois le projet Supabase créé :
// 1. Va dans ton projet Supabase > Project Settings > API
// 2. Copie "Project URL" et colle-le dans SUPABASE_URL ci-dessous
// 3. Copie la clé "anon public" et colle-la dans SUPABASE_ANON_KEY
//
// Ces deux valeurs ne sont PAS secrètes au sens strict (elles sont
// visibles dans le code du site, comme n'importe quelle clé publique
// d'API), c'est normal et attendu pour ce type de projet.
// ============================================================

const SUPABASE_URL = "https://xvbrumwgarkynwjzljzt.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh2YnJ1bXdnYXJreW53anpsanp0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc4OTg4ODUsImV4cCI6MjEwMzQ3NDg4NX0.yYecURzJDr1qTsDWwFtm0LMs16KKIe398Aiytp-fe6k";

// Ne pas toucher à partir d'ici : crée le client utilisé par tout le site
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
