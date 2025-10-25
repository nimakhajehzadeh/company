<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
	import Users from '$lib/components/admin/Users.svelte';
	import { user } from '$lib/stores';
</script>

{#if $user?.role === 'admin' || $user?.role === 'user' }
 <Chat />
{:else if $user?.role === 'adminR'}
<Users/>

{/if}
