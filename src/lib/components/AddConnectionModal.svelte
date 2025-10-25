<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { verifyOpenAIConnection } from '$lib/apis/openai';
	import { verifyOllamaConnection } from '$lib/apis/ollama';

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;
	export let ollama = false;
	export let direct = false;
	export let connection = null;

	let url = '';
	let key = '';
	let connectionType = 'external';
	let enable = true;
	let prefixId = '';
	let tags = [];
	let modelId = '';
	let modelIds = [];
	let loading = false;

	const verifyOllamaHandler = async () => {
		url = url.replace(/\/$/, '');

		const res = await verifyOllamaConnection(localStorage.token, {
			url,
			key
		}).catch((error) => toast.error(`${error}`));

		if (res) toast.success($i18n.t('Server connection verified'));
	};

	const verifyOpenAIHandler = async () => {
		url = url.replace(/\/$/, '');

		const res = await verifyOpenAIConnection(
			localStorage.token,
			{
				url,
				key,
				config: {}
			},
			direct
		).catch((error) => toast.error(`${error}`));

		if (res) toast.success($i18n.t('Server connection verified'));
	};

	const verifyHandler = () => {
		if (ollama) verifyOllamaHandler();
		else verifyOpenAIHandler();
	};

	const addModelHandler = () => {
		if (modelId) {
			modelIds = [...modelIds, modelId];
			modelId = '';
		}
	};

	const submitHandler = async () => {
		loading = true;

		if (!ollama && !url) {
			loading = false;
			toast.error($i18n.t('URL is required'));
			return;
		}

		url = url.replace(/\/$/, '');

		const connection = {
			url,
			key,
			config: {
				enable,
				tags,
				prefix_id: prefixId,
				model_ids: modelIds,
				connection_type: connectionType
			}
		};

		await onSubmit(connection);
		loading = false;
		show = false;

		url = '';
		key = '';
		prefixId = '';
		tags = [];
		modelIds = [];
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			key = connection.key;
			enable = connection.config?.enable ?? true;
			tags = connection.config?.tags ?? [];
			prefixId = connection.config?.prefix_id ?? '';
			modelIds = connection.config?.model_ids ?? [];
			connectionType = connection.config?.connection_type ?? (ollama ? 'local' : 'external');
		}
	};

	$: if (show) init();
	onMount(init);
</script>
