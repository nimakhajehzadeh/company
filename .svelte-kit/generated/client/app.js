export { matchers } from './matchers.js';

export const nodes = [
	() => import('./nodes/0'),
	() => import('./nodes/1'),
	() => import('./nodes/2'),
	() => import('./nodes/3'),
	() => import('./nodes/4'),
	() => import('./nodes/5'),
	() => import('./nodes/6'),
	() => import('./nodes/7'),
	() => import('./nodes/8'),
	() => import('./nodes/9'),
	() => import('./nodes/10'),
	() => import('./nodes/11'),
	() => import('./nodes/12'),
	() => import('./nodes/13'),
	() => import('./nodes/14'),
	() => import('./nodes/15'),
	() => import('./nodes/16'),
	() => import('./nodes/17'),
	() => import('./nodes/18'),
	() => import('./nodes/19'),
	() => import('./nodes/20'),
	() => import('./nodes/21'),
	() => import('./nodes/22'),
	() => import('./nodes/23'),
	() => import('./nodes/24'),
	() => import('./nodes/25'),
	() => import('./nodes/26'),
	() => import('./nodes/27'),
	() => import('./nodes/28'),
	() => import('./nodes/29'),
	() => import('./nodes/30'),
	() => import('./nodes/31'),
	() => import('./nodes/32'),
	() => import('./nodes/33'),
	() => import('./nodes/34'),
	() => import('./nodes/35')
];

export const server_loads = [];

export const dictionary = {
		"/(app)": [7,[2]],
		"/(app)/admin": [8,[2,3]],
		"/(app)/admin/settings": [9,[2,3]],
		"/(app)/admin/settings/[tab]": [10,[2,3]],
		"/(app)/admin/users": [11,[2,3]],
		"/(app)/admin/users/[tab]": [12,[2,3]],
		"/auth": [32],
		"/(app)/channels/[id]": [14,[2]],
		"/(app)/c/[id]": [13,[2]],
		"/error": [33],
		"/(app)/home": [15,[2,4]],
		"/(app)/playground": [16,[2,5]],
		"/(app)/playground/completions": [17,[2,5]],
		"/s/[id]": [34],
		"/watch": [35],
		"/(app)/workspace": [18,[2,6]],
		"/(app)/workspace/functions/create": [19,[2,6]],
		"/(app)/workspace/knowledge": [20,[2,6]],
		"/(app)/workspace/knowledge/create": [21,[2,6]],
		"/(app)/workspace/knowledge/[id]": [22,[2,6]],
		"/(app)/workspace/models": [23,[2,6]],
		"/(app)/workspace/models/create": [24,[2,6]],
		"/(app)/workspace/models/edit": [25,[2,6]],
		"/(app)/workspace/prompts": [26,[2,6]],
		"/(app)/workspace/prompts/create": [27,[2,6]],
		"/(app)/workspace/prompts/edit": [28,[2,6]],
		"/(app)/workspace/tools": [29,[2,6]],
		"/(app)/workspace/tools/create": [30,[2,6]],
		"/(app)/workspace/tools/edit": [31,[2,6]]
	};

export const hooks = {
	handleError: (({ error }) => { console.error(error) }),
	
	reroute: (() => {}),
	transport: {}
};

export const decoders = Object.fromEntries(Object.entries(hooks.transport).map(([k, v]) => [k, v.decode]));

export const hash = false;

export const decode = (type, value) => decoders[type](value);

export { default as root } from '../root.svelte';