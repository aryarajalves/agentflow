import { API_URL, AGENT_API_KEY } from '../config';

const getHeaders = (options = {}) => {
    const headers = {
        ...(options.headers || {}),
        'X-API-Key': AGENT_API_KEY,
    };

    // Adiciona token se autenticado
    const token = localStorage.getItem('admin_token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }

    return headers;
};

export const api = {
    async request(path, options = {}) {
        const url = path.startsWith('http') ? path : `${API_URL}${path}`;
        const finalOptions = {
            ...options,
            headers: getHeaders(options),
        };

        const response = await fetch(url, finalOptions);

        if (response.status === 401) {
            // Token expirado ou inválido: desloga automaticamente e manda para a tela de login
            localStorage.removeItem('admin_token');
            localStorage.removeItem('user_name');
            localStorage.removeItem('user_role');
            sessionStorage.setItem('session_expired_msg', 'Sua sessão expirou. Faça login novamente para continuar.');
            
            const isPublicRoute = 
                window.location.pathname.startsWith('/chat/') || 
                window.location.pathname.startsWith('/shared/') ||
                window.location.pathname.startsWith('/public/');
                
            if (!isPublicRoute && window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }

        return response;
    },

    get(path, options = {}) {
        // cache: 'no-store' evita que o navegador (ou um proxy/CDN na frente da API, ex.: túnel
        // Cloudflare) sirva uma resposta antiga em cache para este GET — relevante para telas de
        // configuração (ex.: Editar Integração) onde o valor precisa refletir a última gravação.
        return this.request(path, { ...options, method: 'GET', cache: options.cache || 'no-store' });
    },

    post(path, body, options = {}) {
        return this.request(path, { ...options, method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) });
    },

    put(path, body, options = {}) {
        return this.request(path, { ...options, method: 'PUT', body: body instanceof FormData ? body : JSON.stringify(body) });
    },

    patch(path, body, options = {}) {
        return this.request(path, { ...options, method: 'PATCH', body: body instanceof FormData ? body : JSON.stringify(body) });
    },

    delete(path, body, options = {}) {
        const fetchOptions = { ...options, method: 'DELETE' };
        if (body) {
            fetchOptions.body = body instanceof FormData ? body : JSON.stringify(body);
        }
        return this.request(path, fetchOptions);
    },

    upload(path, formData, { onProgress } = {}) {
        const url = path.startsWith('http') ? path : `${API_URL}${path}`;
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            
            const headers = getHeaders({ body: formData });
            Object.keys(headers).forEach(key => {
                xhr.setRequestHeader(key, headers[key]);
            });

            if (onProgress) {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        onProgress(percent);
                    }
                });
            }

            xhr.onload = () => {
                const response = {
                    ok: xhr.status >= 200 && xhr.status < 300,
                    status: xhr.status,
                    json: async () => JSON.parse(xhr.responseText)
                };
                resolve(response);
            };

            xhr.onerror = () => reject(new Error('A conexão falhou. Se o vídeo for grande, pode ser bloqueio de tamanho no seu Proxy ou Cloudflare (CORS error).'));
            xhr.send(formData);
        });
    }
};
