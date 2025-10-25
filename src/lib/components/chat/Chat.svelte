<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { tick } from 'svelte';
	import { generateChatCompletion } from '$lib/apis/ollama';

	// Editable text fields
	let editableText = 'کلیک کرده و مبحث درس را وارد کنید';
	let editableText2 = 'کلیک کرده و مبحث مورد علاقه را وارد کنید';
	let isEditing = false, isEditing2 = false;
	let inputRef, inputRef2;
	let hasContent = false, hasContent2 = false;

	// Streaming text output
	let streamedText = ''; // will be shown in .text-container
	let isStreaming = false;

	// Watch content status
	$: hasContent = editableText.trim().length > 0;
	$: hasContent2 = editableText2.trim().length > 0;

	// Editable input handlers (combined)
	const startEditing = (n: number) => {
		if (n === 1) {
			isEditing = true;
			tick().then(() => inputRef?.focus());
		} else {
			isEditing2 = true;
			tick().then(() => inputRef2?.focus());
		}
	};

	const stopEditing = (n: number) => {
		if (n === 1) {
			isEditing = false;
			if (!editableText.trim()) editableText = 'کلیک کرده و مبحث درس را وارد کنید';
		} else {
			isEditing2 = false;
			if (!editableText2.trim()) editableText2 = 'کلیک کرده و مبحث مورد علاقه را وارد کنید';
		}
	};

	const handleKeydown = (event, n: number) => {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			stopEditing(n);
		} else if (event.key === 'Escape') {
			event.preventDefault();
			stopEditing(n);
		}
	};

	// 🚀 Button click — send concatenated prompt to API and stream
	const handleButtonClick = async () => {
		if (!hasContent || !hasContent2) {
			toast.warning('لطفاً هر دو فیلد را تکمیل کنید');
			return;
		}

		const finalPrompt = `${editableText}\n${editableText2}`;
		streamedText = '';
		isStreaming = true;

		try {
			const response = await generateChatCompletion(finalPrompt, {
				stream: true
			});

			// ✅ Stream the response text chunk by chunk
			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			while (true) {
				const { value, done } = await reader.read();
				if (done) break;
				streamedText += decoder.decode(value, { stream: true });
				await tick(); // update UI
			}
			toast.success('پاسخ با موفقیت دریافت شد');
		} catch (err) {
			console.error('Error streaming response:', err);
			toast.error('خطا در دریافت پاسخ');
		} finally {
			isStreaming = false;
		}
	};
</script>
