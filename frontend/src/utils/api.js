/**
 * api.js — Cliente HTTP centralizado
 * ====================================
 * Todas las llamadas a la API del backend pasan por este módulo.
 *
 * Características:
 *  - Base URL configurable desde la variable de entorno VITE_API_URL.
 *  - Adjunta automáticamente el JWT Bearer token desde localStorage en cada request.
 *  - Lanza errores descriptivos cuando el servidor retorna status >= 400.
 *  - Expone funciones organizadas por dominio: auth, games, user, cards, teams, shop.
 *
 * Uso:
 *  import { auth, games, user, teams } from '../utils/api';
 *  const { access_token } = await auth.login('usuario', 'contraseña');
 *  const game = await games.create({ ... });
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Helpers internos
// ---------------------------------------------------------------------------

/**
 * Construye los headers base para cada request.
 * Incluye el JWT si existe en localStorage.
 */
function _buildHeaders(extra = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...extra,
  };
  const token = localStorage.getItem('jwt_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Realiza un fetch y lanza un Error con el detalle del servidor si el status >= 400.
 * @param {string} path  - Ruta relativa al BASE_URL (ej. "/api/v1/auth/login")
 * @param {RequestInit} options - Opciones del fetch
 * @returns {Promise<any>} - JSON parseado de la respuesta
 */
async function _request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: _buildHeaders(options.headers || {}),
  });

  if (!response.ok) {
    let errorDetail = `Error ${response.status}`;
    try {
      const errorBody = await response.json();
      
      // Si detail es un array (errores de validación de Pydantic), tomar el primer error
      if (Array.isArray(errorBody.detail)) {
        if (errorBody.detail.length > 0 && typeof errorBody.detail[0] === 'object') {
          errorDetail = errorBody.detail[0].msg || errorBody.detail[0].detail || 'Error de validación';
        } else if (errorBody.detail.length > 0) {
          errorDetail = errorBody.detail[0];
        }
      } else if (typeof errorBody.detail === 'string') {
        errorDetail = errorBody.detail;
      }
    } catch {
      // El body no es JSON, usar el status text
      errorDetail = response.statusText || errorDetail;
    }
    throw new Error(errorDetail);
  }

  // 204 No Content no tiene body
  if (response.status === 204) return null;
  return response.json();
}

// ---------------------------------------------------------------------------
// auth — Registro e inicio de sesión
// ---------------------------------------------------------------------------

export const auth = {
  /**
   * Registra un nuevo usuario.
   * @param {string} username
   * @param {string} password
   * @returns {{ status: string, user_id: string, username: string }}
   */
  register: (username, password) =>
    _request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  /**
   * Inicia sesión y retorna el JWT + datos del usuario.
   * El token y user_id se guardan automáticamente en localStorage.
   * @param {string} username
   * @param {string} password
   * @returns {{ access_token: string, token_type: string, user_id: string, username: string }}
   */
  login: async (username, password) => {
    // El endpoint usa OAuth2PasswordRequestForm (form-data, no JSON)
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || 'Credenciales incorrectas.');
    }

    const data = await response.json();
    localStorage.setItem('jwt_token', data.access_token);
    localStorage.setItem('user_id', data.user_id);
    localStorage.setItem('username', data.username);
    return data;
  },

  /**
   * Cierra la sesión limpiando el token del localStorage.
   */
  logout: () => {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
  },

  /**
   * Retorna los datos del usuario autenticado desde localStorage, o null si no hay sesión.
   * @returns {{ userId: string, username: string } | null}
   */
  getCurrentUser: () => {
    const userId = localStorage.getItem('user_id');
    const username = localStorage.getItem('username');
    if (!userId) return null;
    return { userId, username };
  },
};

// ---------------------------------------------------------------------------
// games — Creación y estado de partidas
// ---------------------------------------------------------------------------

export const games = {
  /**
   * Crea una nueva sesión de juego 1v1.
   * @param {{ home_user_id, away_user_id, game_mode, difficulty, home_pitcher_id,
   *           away_pitcher_id, home_lineup, away_lineup,
   *           home_tactics_deck, away_tactics_deck }} payload
   * @returns {GameSessionResponse}
   */
  create: (payload) =>
    _request('/api/v1/games/create', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Obtiene el estado sanitizado de una partida (Fog of War aplicado).
   * @param {string} gameId
   * @param {string} userId - ID del usuario que consulta (determina qué se oculta)
   * @returns {GameSessionResponse}
   */
  getState: (gameId, userId) =>
    _request(`/api/v1/games/${gameId}?user_id=${userId}`),

  /**
   * Registra el picheo del lanzador (Fase 1 del at-bat).
   * @param {string} gameId
   * @param {{ pitch_type: string, zone: number }} payload
   */
  pitch: (gameId, payload) =>
    _request(`/api/v1/games/${gameId}/pitch`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Ejecuta el swing del bateador y resuelve la jugada (Fase 2+3).
   * @param {string} gameId
   * @param {{ swing_type: string, guessed_zone: number|null, guessed_pitch: string|null }} payload
   * @returns {PlayResultResponse}
   */
  swing: (gameId, payload) =>
    _request(`/api/v1/games/${gameId}/swing`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Activa una carta táctica antes del enfrentamiento.
   * @param {string} gameId
   * @param {{ player_role: string, tactic_id: string }} payload
   */
  playTactic: (gameId, payload) =>
    _request(`/api/v1/games/${gameId}/play-tactic`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Realiza un cambio de pitcher desde el bullpen.
   * @param {string} gameId
   * @param {{ new_pitcher_id: string }} payload
   */
  changePitcher: (gameId, payload) =>
    _request(`/api/v1/games/${gameId}/change-pitcher`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Obtiene los lanzadores disponibles en el bullpen.
   * @param {string} gameId
   * @returns {Promise<{available_pitchers: Array}>}
   */
  getAvailablePitchers: (gameId) => {
    const url = `/api/v1/games/${gameId}/available-pitchers`;
    console.log(`📡 GET request a: ${url}`);
    return _request(url, { method: 'GET' });
  },

  /**
   * Intenta un robo de base.
   * @param {string} gameId
   * @param {{ target_base: '2b' | '3b' }} payload
   */
  steal: (gameId, payload) =>
    _request(`/api/v1/games/${gameId}/steal`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /**
   * Obtiene el box score (resumen de estadísticas) de una partida.
   * @param {string} gameId
   * @returns {Promise<{game_id, final_score, box_score}>}
   */
  getBoxScore: (gameId) =>
    _request(`/api/v1/games/${gameId}/box-score`),

  /**
   * Obtiene las estadísticas de un jugador específico en una partida.
   * @param {string} gameId
   * @param {string} playerId
   * @returns {Promise<{game_id, player_id, stats}>}
   */
  getPlayerGameStats: (gameId, playerId) =>
    _request(`/api/v1/games/${gameId}/player/${playerId}/stats`),
};

// ---------------------------------------------------------------------------
// user — Perfil, inventario, alineación y club
// ---------------------------------------------------------------------------

export const user = {
  /**
   * Obtiene el perfil y wallet del usuario.
   * @param {string} userId
   * @returns {UserProfileResponseSchema}
   */
  getProfile: (userId) => _request(`/api/v1/user/${userId}/profile`),

  /**
   * Obtiene el inventario de cartas del usuario.
   * @param {string} userId
   * @returns {UserInventoryResponseSchema}
   */
  getInventory: (userId) => _request(`/api/v1/user/${userId}/inventory`),

  /**
   * Obtiene la alineación (lineup) activa del usuario desde la base de datos.
   * @param {string} userId
   * @returns {Promise<Object>}
   */
  getLineup: (userId) => _request(`/api/v1/user/${userId}/lineup`),

  /**
   * Actualiza o crea la alineación activa del usuario en la base de datos.
   * @param {string} userId
   * @param {Object} lineupData - Objeto con el mapeo de posiciones {"P": card, "C": card, ...}
   * @returns {Promise<Object>}
   */
  updateLineup: (userId, lineupData) =>
    _request(`/api/v1/user/${userId}/lineup`, {
      method: 'PUT',
      body: JSON.stringify({
        name: 'Lineup Principal',
        is_active: true,
        slots: lineupData,
      }),
    }),

  /**
   * Registra un nuevo club personalizado para el usuario.
   * @param {string} userId
   * @param {Object} teamData
   * @returns {Promise<Object>}
   */
  createTeam: (userId, teamData) =>
    _request(`/api/v1/user/${userId}/team`, {
      method: 'POST',
      body: JSON.stringify(teamData),
    }),

  /**
   * Obtiene los datos del club personalizado del usuario.
   * @param {string} userId
   * @returns {Promise<Object>}
   */
  getTeam: (userId) => _request(`/api/v1/user/${userId}/team`),

  /**
   * Obtiene las métricas calculadas del equipo del usuario (Overall, Bateo, Pitcheo).
   * @param {string} userId - ID del usuario.
   * @returns {Promise<{overall: number, batOvr: number, pitOvr: number}>}
   */
  getTeamStats: (userId) => _request(`/api/v1/user/${userId}/team-stats`),

  /**
   * Obtiene todos los equipos disponibles para seleccionar como franquicia base.
   * @returns {Promise<Array>} - Array de equipos con id, name, city, color, badge, desc
   */
  getAvailableTeams: () => _request('/api/v1/teams/cpu'),
};

// ---------------------------------------------------------------------------
// cards — Catálogo de equipos y cartas
// ---------------------------------------------------------------------------

export const cards = {
  /**
   * Lista todos los equipos disponibles.
   * @returns {TeamBaseSchema[]}
   */
  getTeams: () => _request('/api/v1/cards/teams'),

  /**
   * Obtiene el roster completo de un equipo.
   * @param {string} teamId - Ej. "NYY", "LAD"
   * @returns {TeamRosterResponseSchema}
   */
  getTeamRoster: (teamId) => _request(`/api/v1/cards/teams/${teamId}`),

  /**
   * Obtiene el detalle de una carta específica.
   * @param {string} cardId
   * @returns {PlayerCardSchema}
   */
  getCard: (cardId) => _request(`/api/v1/cards/${cardId}`),
};

// ---------------------------------------------------------------------------
// teams — Equipos CPU y rivales
// ---------------------------------------------------------------------------

export const teams = {
  /**
   * Obtiene la lista de equipos CPU disponibles con sus métricas (OVR, BAT, PIT).
   * @returns {Promise<Array>}
   */
  getCpuTeams: () => _request('/api/v1/teams/cpu'),
};

// ---------------------------------------------------------------------------
// shop — Tienda de sobres
// ---------------------------------------------------------------------------

export const shop = {
  /**
   * Asigna el starter pack de un equipo al inventario del usuario.
   * @param {string} userId
   * @param {string} teamId
   * @returns {StarterPackResponseSchema}
   */
  claimStarterPack: (userId, teamId) =>
    _request(`/api/v1/shop/starter-pack?user_id=${userId}&team_id=${teamId}`, {
      method: 'POST',
    }),

  /**
   * Abre un sobre de cartas (descuenta stamps del wallet).
   * @param {string} userId
   * @param {'BRONZE' | 'GOLD' | 'DIAMOND'} packType
   * @returns {OpenPackResponseSchema}
   */
  openPack: (userId, packType) =>
    _request(`/api/v1/shop/open-pack?user_id=${userId}&pack_type=${packType}`, {
      method: 'POST',
    }),
};