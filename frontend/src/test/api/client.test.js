/**
 * =============================================
 * TESTES UNITÁRIOS: API Client
 * =============================================
 * Mapeia todas as ações:
 * 1. GET/POST/PUT/DELETE com headers corretos
 * 2. X-API-Key em todas as requisições
 * 3. Authorization Bearer com JWT
 * 4. Content-Type application/json
 * 5. Interceptor de 401 (remove token, redireciona)
 * 6. Resolução de URLs relativas/absolutas
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('API Client Module', () => {
    let api;
    const originalFetch = global.fetch;

    beforeEach(async () => {
        global.fetch = vi.fn();
        vi.resetModules();

        vi.doMock('../../config', () => ({
            API_URL: 'http://test-api:8002',
            AGENT_API_KEY: 'my-secret-key',
        }));

        const module = await import('../../api/client');
        api = module.api;
    });

    afterEach(() => {
        global.fetch = originalFetch;
        vi.restoreAllMocks();
    });

    // ===== HEADERS =====
    describe('Headers de Requisição', () => {
        it('deve incluir X-API-Key em todas as requisições', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.get('/agents');

            expect(global.fetch).toHaveBeenCalledWith(
                'http://test-api:8002/agents',
                expect.objectContaining({
                    headers: expect.objectContaining({ 'X-API-Key': 'my-secret-key' }),
                })
            );
        });

        it('deve incluir Authorization Bearer quando token existe', async () => {
            localStorage.setItem('admin_token', 'jwt-token-abc');
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.get('/agents');

            expect(global.fetch).toHaveBeenCalledWith(
                expect.any(String),
                expect.objectContaining({
                    headers: expect.objectContaining({ 'Authorization': 'Bearer jwt-token-abc' }),
                })
            );
        });

        it('deve incluir Content-Type application/json para body não FormData', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.post('/agents', { name: 'Test' });

            expect(global.fetch).toHaveBeenCalledWith(
                expect.any(String),
                expect.objectContaining({
                    headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
                })
            );
        });
    });

    // ===== MÉTODOS HTTP =====
    describe('Métodos HTTP', () => {
        it('GET deve usar method GET', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.get('/models');
            expect(global.fetch).toHaveBeenCalledWith('http://test-api:8002/models', expect.objectContaining({ method: 'GET' }));
        });

        it('POST deve usar method POST e enviar body como JSON string', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            const payload = { name: 'Novo Agente', model: 'gpt-4o' };
            await api.post('/agents', payload);
            expect(global.fetch).toHaveBeenCalledWith('http://test-api:8002/agents', expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) }));
        });

        it('PUT deve usar method PUT e enviar body como JSON string', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            const payload = { name: 'Agente Editado' };
            await api.put('/agents/1', payload);
            expect(global.fetch).toHaveBeenCalledWith('http://test-api:8002/agents/1', expect.objectContaining({ method: 'PUT', body: JSON.stringify(payload) }));
        });

        it('DELETE deve usar method DELETE', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.delete('/agents/1');
            expect(global.fetch).toHaveBeenCalledWith('http://test-api:8002/agents/1', expect.objectContaining({ method: 'DELETE' }));
        });
    });

    // ===== 401 INTERCEPTOR =====
    describe('Interceptor de Autenticação (401)', () => {
        it('deve remover token, dados de usuário e definir mensagem de expiração em caso de 401', async () => {
            localStorage.setItem('admin_token', 'expired-token');
            localStorage.setItem('user_name', 'Aryaraj');
            localStorage.setItem('user_role', 'Super Admin');
            window.location.pathname = '/dashboard';
            global.fetch.mockResolvedValue({ status: 401, ok: false });

            await api.get('/agents');
            expect(localStorage.getItem('admin_token')).toBeNull();
            expect(localStorage.getItem('user_name')).toBeNull();
            expect(localStorage.getItem('user_role')).toBeNull();
            expect(sessionStorage.getItem('session_expired_msg')).toBe('Sua sessão expirou. Faça login novamente para continuar.');
        });
    });

    // ===== URL =====
    describe('Resolução de URL', () => {
        it('deve usar API_URL como base para paths relativos', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.get('/dashboard/stats');
            expect(global.fetch).toHaveBeenCalledWith('http://test-api:8002/dashboard/stats', expect.any(Object));
        });

        it('deve usar URL absoluta quando fornecida', async () => {
            global.fetch.mockResolvedValue({ status: 200, ok: true });
            await api.get('https://external-api.com/data');
            expect(global.fetch).toHaveBeenCalledWith('https://external-api.com/data', expect.any(Object));
        });
    });
});
