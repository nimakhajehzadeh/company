<script lang="ts">
	import { getContext } from 'svelte';
	import { showSidebar, user, isApp, WEBUI_NAME } from '$lib/stores';
	

	const i18n = getContext('i18n');

	const isWindows = /Windows/i.test(navigator.userAgent);

	// Force sidebar to always be visible
	showSidebar.set(true);

	// Active item state
	 // Active item state
	let activeItem = 'group1';

	// تعریف آیتم‌ها بر اساس نقش
	let navItems = [];

	$: {
		if ($user?.role === 'user') {
			// کاربر عادی = ۶ آیتم
			navItems = [
				{ id: 'group1', label: 'گروه ۱', icon: '📚', description: 'مواد آموزشی' },
				{ id: 'group2', label: 'گروه ۲', icon: '🎓', description: 'پیشرفت تحصیلی' },
				{ id: 'group3', label: 'گروه ۳', icon: '👩‍🏫', description: 'منابع تدریس' },
				{ id: 'group4', label: 'گروه ۴', icon: '📝', description: 'تکالیف و آزمون‌ها' },
				{ id: 'group5', label: 'گروه ۵', icon: '🧠', description: 'پایگاه دانش' },
				{ id: 'group6', label: 'گروه ۶', icon: '💡', description: 'نکات و پیشنهادات' }
			];
		} else if ($user?.role === 'admin') {
			// ادمین = ۵ آیتم
			navItems = [
				{ id: 'group1', label: 'گروه ۱', icon: '📚', description: 'مواد آموزشی' },
				{ id: 'group2', label: 'گروه ۲', icon: '🎓', description: 'پیشرفت تحصیلی' },
				{ id: 'group3', label: 'گروه ۳', icon: '👩‍🏫', description: 'منابع تدریس' },
				{ id: 'group4', label: 'گروه ۴', icon: '📝', description: 'تکالیف و آزمون‌ها' },
				{ id: 'group5', label: 'گروه ۵', icon: '🧠', description: 'پایگاه دانش' }
			];
		}
	}


	function handleItemClick(itemId: string) {
		activeItem = itemId;
		// Add your navigation logic here
		console.log(`Navigating to: ${itemId}`);
	}
</script>

<!-- Always show the sidebar -->
<div
	id="sidebar"
	class="h-screen max-h-[100dvh] min-h-screen select-none bg-gray-50 dark:bg-gray-950 z-50 {$isApp
		? `ml-[4.5rem] md:ml-0 `
		: ' transition-all duration-300 '} shrink-0 text-gray-900 dark:text-gray-200 text-sm fixed top-0 left-0 overflow-x-hidden border-r border-gray-200 dark:border-gray-800"
>
	<div
		class=" my-auto flex flex-col h-screen max-h-[100dvh] w-[260px] overflow-x-hidden scrollbar-hidden z-50"
	>
		<!-- Fancy Header -->
		<div
			class="sidebar px-4 pt-4 pb-4 sticky top-0 z-10 bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-950 dark:via-gray-900 dark:to-gray-800 border-b border-gray-200/50 dark:border-gray-700/50 backdrop-blur-sm"
		>
			<div class="relative">
				<!-- Background decorative elements -->
				<div class="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 rounded-2xl"></div>
				<div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-blue-400/10 to-purple-600/10 rounded-full blur-xl"></div>
				<div class="absolute bottom-0 left-0 w-12 h-12 bg-gradient-to-tr from-purple-400/10 to-pink-600/10 rounded-full blur-lg"></div>
				
				<!-- Main content -->
				<div class="relative flex items-center justify-between p-3 rounded-2xl backdrop-blur-sm bg-white/30 dark:bg-gray-800/30 border border-gray-200/30 dark:border-gray-700/30 shadow-lg">
					<!-- Title section -->
					<div class="flex-1">
						<div class="relative">
							<!-- Gradient text with glow effect -->
							<h1 class="font-bold text-lg bg-gradient-to-r from-gray-900 via-blue-800 to-purple-800 dark:from-white dark:via-blue-200 dark:to-purple-200 bg-clip-text text-transparent leading-tight">
								{$WEBUI_NAME}
							</h1>
							
							<!-- Subtitle with animated dots -->
							<div class="flex items-center space-x-1 mt-1">
								<span class="text-xs text-gray-500 dark:text-gray-400 font-medium">دستیار هوش مصنوعی</span>
								<div class="flex space-x-1">
									<div class="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
									<div class="w-1 h-1 bg-purple-400 rounded-full animate-pulse delay-100"></div>
									<div class="w-1 h-1 bg-pink-400 rounded-full animate-pulse delay-200"></div>
								</div>
							</div>
						</div>
					</div>

					<!-- Status badge -->
					<div class="flex items-center">
						<div class="relative px-2 py-1 rounded-full bg-gradient-to-r from-green-400 to-emerald-500 shadow-lg">
							<div class="flex items-center space-x-1">
								<div class="w-2 h-2 bg-white rounded-full animate-pulse"></div>
								<span class="text-xs font-medium text-white">حرفه‌ای</span>
							</div>
							<!-- Glow effect -->
							<div class="absolute inset-0 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full blur-md opacity-50"></div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- User Role Section (only show for students) -->
		{#if $user?.role === 'user'}
			<div class="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50">
				<div class="relative bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 rounded-xl p-3 border border-blue-200/50 dark:border-blue-700/30">
					<!-- Background decorative element -->
					<div class="absolute top-0 right-0 w-8 h-8 bg-gradient-to-br from-blue-400/20 to-indigo-600/20 rounded-full blur-sm"></div>
					
					<div class="relative flex items-center space-x-3">
						<!-- Student icon -->
						<div class="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg">
							<span class="text-white text-lg">🎓</span>
						</div>
						
						<!-- Role info -->
						<div class="flex-1 min-w-0">
							<div class="font-semibold text-sm text-blue-800 dark:text-blue-200">
								نقش کاربری
							</div>
							<div class="flex items-center space-x-2 mt-1">
								<span class="text-xs font-medium text-blue-600 dark:text-blue-300">
									دانشجو
								</span>
								<div class="w-1 h-1 bg-blue-400 rounded-full"></div>
								<span class="text-xs text-blue-500/80 dark:text-blue-300/80">
									فعال
								</span>
							</div>
						</div>
						
						<!-- Status indicator -->
						<div class="flex-shrink-0">
							<div class="w-8 h-8 bg-white/80 dark:bg-gray-800/80 rounded-full flex items-center justify-center backdrop-blur-sm border border-blue-200/50 dark:border-blue-600/30">
								<div class="w-3 h-3 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full animate-pulse shadow-sm"></div>
							</div>
						</div>
					</div>
					
					<!-- Academic level or additional info -->
					<div class="mt-2 pt-2 border-t border-blue-200/30 dark:border-blue-600/20">
						<div class="flex items-center justify-between text-xs">
							<span class="text-blue-600/80 dark:text-blue-300/80">نوع دانشجو :</span>
							<span class="font-medium text-blue-700 dark:text-blue-200">{$user?.role}</span>
						</div>
					</div>
				</div>
			</div>
		{/if}


		{#if $user?.role === 'admin'}
			<div class="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50">
				<div class="relative bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 rounded-xl p-3 border border-blue-200/50 dark:border-blue-700/30">
					<!-- Background decorative element -->
					<div class="absolute top-0 right-0 w-8 h-8 bg-gradient-to-br from-blue-400/20 to-indigo-600/20 rounded-full blur-sm"></div>
					
					<div class="relative flex items-center space-x-3">
						<!-- Student icon -->
						<div class="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg">
							<span class="text-white text-lg">🎓</span>
						</div>
						
						<!-- Role info -->
						<div class="flex-1 min-w-0">
							<div class="font-semibold text-sm text-blue-800 dark:text-blue-200">
								نقش کاربری
							</div>
							<div class="flex items-center space-x-2 mt-1">
								<span class="text-xs font-medium text-blue-600 dark:text-blue-300">
									معلم
								</span>
								<div class="w-1 h-1 bg-blue-400 rounded-full"></div>
								<span class="text-xs text-blue-500/80 dark:text-blue-300/80">
									فعال
								</span>
							</div>
						</div>
						
						<!-- Status indicator -->
						<div class="flex-shrink-0">
							<div class="w-8 h-8 bg-white/80 dark:bg-gray-800/80 rounded-full flex items-center justify-center backdrop-blur-sm border border-blue-200/50 dark:border-blue-600/30">
								<div class="w-3 h-3 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full animate-pulse shadow-sm"></div>
							</div>
						</div>
					</div>
					
					
				</div>
			</div>
		{/if}

		<!-- Navigation Items -->
		<div class="flex-1 px-2 py-4 space-y-2 overflow-y-auto">
			{#each navItems as item}
				<button
					class="w-full group relative flex items-center px-3 py-3 text-left rounded-xl transition-all duration-200 hover:scale-[1.02] {
						activeItem === item.id
							? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/25 dark:shadow-purple-500/25'
							: 'hover:bg-white dark:hover:bg-gray-800 hover:shadow-md text-gray-700 dark:text-gray-300'
					}"
					on:click={() => handleItemClick(item.id)}
				>
					<!-- Icon with fancy background -->
					<div class="relative">
						<div class="flex items-center justify-center w-10 h-10 rounded-lg {
							activeItem === item.id 
								? 'bg-white/20 backdrop-blur-sm' 
								: 'bg-gray-100 dark:bg-gray-700 group-hover:bg-gray-200 dark:group-hover:bg-gray-600'
							} transition-all duration-200">
							<span class="text-lg">{item.icon}</span>
						</div>
						
						<!-- Active indicator -->
						{#if activeItem === item.id}
							<div class="absolute -right-1 -top-1 w-3 h-3 bg-white rounded-full shadow-sm">
								<div class="w-2 h-2 bg-green-500 rounded-full m-0.5 animate-pulse"></div>
							</div>
						{/if}
					</div>

					<!-- Text content -->
					<div class="ml-3 flex-1 min-w-0">
						<div class="font-medium text-sm truncate">
							{item.label}
						</div>
						<div class="text-xs opacity-75 truncate mt-0.5 {
							activeItem === item.id ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'
						}">
							{item.description}
						</div>
					</div>

					<!-- Hover arrow indicator -->
					<div class="opacity-0 group-hover:opacity-100 transition-opacity duration-200 {
						activeItem === item.id ? 'opacity-100' : ''
					}">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
						</svg>
					</div>
				</button>
			{/each}
		</div>

		<!-- Footer -->
		<div class="px-1.5 pt-1.5 pb-2 sticky bottom-0 z-10 bg-gray-50 dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 sidebar">
			<div class="flex flex-col font-primary">
				<div class="text-center text-xs text-gray-500 dark:text-gray-400 mb-2">
					{$WEBUI_NAME}
				</div>
				
				<!-- Status indicator -->
				<div class="flex items-center justify-center space-x-2 text-xs">
					<div class="flex items-center space-x-1">
						<div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
						<span class="text-gray-600 dark:text-gray-400">آنلاین</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}

	/* Custom scrollbar styling */
	.scrollbar-hidden::-webkit-scrollbar {
		width: 4px;
	}
	.scrollbar-hidden::-webkit-scrollbar-track {
		background: transparent;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 2px;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.8);
	}

	/* Animation for active state */
	@keyframes slideIn {
		from {
			transform: translateX(-10px);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	/* Custom glow animation */
	@keyframes glow {
		0%, 100% { opacity: 0.5; }
		50% { opacity: 1; }
	}
</style>
