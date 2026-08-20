import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  es: {
    translation: {
      // General & Header
      "app.subtitle": "BASEBALL TÁCTICO 1V1",
      "app.tradition": "★ TRADICIÓN Y ESTRATEGIA ★",
      // Auth Screen
      "auth.login_tab": "INGRESAR",
      "auth.register_tab": "REGISTRO",
      "auth.username_label": "NOMBRE DE JUGADOR / USUARIO",
      "auth.password_label": "CONTRASEÑA",
      "auth.submit_login": "ENTRAR AL ESTADIO",
      "auth.submit_register": "CREAR JUGADOR",
      // Lobby
      "lobby.manager": "MÁNAGER ACTIVO",
      "lobby.logout": "SALIR",
      "lobby.select_mode": "SELECCIONAR MODO DE JUEGO",
      "lobby.vs_cpu": "VS CPU",
      "lobby.vs_cpu_desc": "PARTIDA RÁPIDA SOLITARIO",
      "lobby.pvp": "1V1 ONLINE",
      "lobby.pvp_desc": "DESAFÍO MULTIJUGADOR",
      "lobby.cpu_difficulty": "DIFICULTAD DE LA CPU",
      "lobby.diff_easy": "FÁCIL",
      "lobby.diff_medium": "MEDIA",
      "lobby.diff_hard": "DIFÍCIL",
      "lobby.start": "INICIAR PARTIDA VS CPU", // <--- Clave corregida
      "lobby.start_pvp": "BUSCAR RIVAL ONLINE",
      // PlayerCard
      "card.pitcher": "PÍCHER",
      "card.batter": "BATEADOR",
      "card.velocity": "VEL",
      "card.control": "CTL",
      "card.power": "PWR",
      "card.contact": "CON"
    }
  },
  en: {
    translation: {
      // General & Header
      "app.subtitle": "1V1 TACTICAL BASEBALL",
      "app.tradition": "★ TRADITION & STRATEGY ★",
      // Auth Screen
      "auth.login_tab": "LOG IN",
      "auth.register_tab": "REGISTER",
      "auth.username_label": "PLAYER NAME / USERNAME",
      "auth.password_label": "PASSWORD",
      "auth.submit_login": "ENTER STADIUM",
      "auth.submit_register": "CREATE PLAYER",
      // Lobby
      "lobby.manager": "ACTIVE MANAGER",
      "lobby.logout": "LOGOUT",
      "lobby.select_mode": "SELECT GAME MODE",
      "lobby.vs_cpu": "VS CPU",
      "lobby.vs_cpu_desc": "SOLO QUICK MATCH",
      "lobby.pvp": "1V1 ONLINE",
      "lobby.pvp_desc": "MULTIPLAYER CHALLENGE",
      "lobby.cpu_difficulty": "CPU DIFFICULTY",
      "lobby.diff_easy": "EASY",
      "lobby.diff_medium": "MEDIUM",
      "lobby.diff_hard": "HARD",
      "lobby.start": "START CPU MATCH", // <--- Clave corregida
      "lobby.start_pvp": "FIND ONLINE RIVAL",
      // PlayerCard
      "card.pitcher": "PITCHER",
      "card.batter": "BATTER",
      "card.velocity": "VEL",
      "card.control": "CTL",
      "card.power": "PWR",
      "card.contact": "CON"
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'es',
    fallbackLng: 'es',
    interpolation: { escapeValue: false }
  });

export default i18n;