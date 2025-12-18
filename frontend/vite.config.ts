import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: 'http://backend:8000',
				changeOrigin: true
			},
			'/audit': {
				target: 'http://backend:8000',
				changeOrigin: true
			},
			'/health': {
				target: 'http://backend:8000',
				changeOrigin: true
			},
			'/models': {
				target: 'http://backend:8000',
				changeOrigin: true
			}
		}
	}
});
