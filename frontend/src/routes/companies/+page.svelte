<script lang="ts">
  import { onMount } from 'svelte';
  import { Building2, Plus, Edit, Trash2, AlertCircle } from 'lucide-svelte';
  import { api, type Company } from '$lib/api';
  
  let companies: Company[] = [];
  let loading = true;
  let error = '';

  onMount(async () => {
    await loadCompanies();
  });

  async function loadCompanies() {
    try {
      loading = true;
      companies = await api.listCompanies();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането';
    } finally {
      loading = false;
    }
  }

  async function deleteCompany(id: number) {
    const company = companies.find(c => c.id === id);
    if (!company) return;
    
    try {
      // First try regular delete to get info about associated data
      await api.deleteCompany(id, false);
      await loadCompanies();
    } catch (e) {
      // Parse the error - it might be a structured error from the backend
      let errorInfo: any = {};
      let errorMsg = 'Грешка при изтриването';
      
      if (e instanceof Error) {
        console.log('Delete error:', e.message); // Debug log
        try {
          // Try to parse the error message as JSON (FastAPI returns structured errors)
          const errorData = JSON.parse(e.message);
          console.log('Parsed error data:', errorData); // Debug log
          
          if (errorData.detail && typeof errorData.detail === 'object') {
            errorInfo = errorData.detail;
            errorMsg = errorInfo.message || errorInfo.error || 'Фирмата има свързани данни';
          } else if (errorData.detail) {
            errorMsg = errorData.detail;
            // Try to extract info from string message
            if (errorMsg.includes('existing data') || errorMsg.includes('existing transactions')) {
              errorInfo.hasData = true;
            }
          } else {
            errorMsg = e.message;
          }
        } catch (parseError) {
          // If parsing fails, use the original message
          console.log('JSON parse failed:', parseError);
          errorMsg = e.message;
          // Check if it looks like it has associated data
          if (errorMsg.includes('existing data') || errorMsg.includes('existing transactions')) {
            errorInfo.hasData = true;
          }
        }
      }
      
      // Check if it's the "has associated data" error
      if (errorMsg.includes('existing data') || errorMsg.includes('existing transactions') || errorInfo.counts || errorInfo.hasData) {
        // Build detailed message from structured error
        let confirmMessage = `Фирмата "${company.name}" има свързани данни:\n\n`;
        
        if (errorInfo.counts) {
          const { purchases, sales, declarations } = errorInfo.counts;
          if (purchases > 0) confirmMessage += `• ${purchases} записа от дневника на покупките\n`;
          if (sales > 0) confirmMessage += `• ${sales} записа от дневника за продажбите\n`;
          if (declarations > 0) confirmMessage += `• ${declarations} ДДС декларации\n`;
        } else {
          // Fallback when we don't have exact counts
          confirmMessage += `• Дневници на покупки и/или продажби\n• ДДС декларации\n`;
        }
        
        confirmMessage += '\nИскате ли да изтриете фирмата заедно с всички свързани данни?\n\n⚠️ ВНИМАНИЕ: Това действие е необратимо!';
        
        const confirmed = confirm(confirmMessage);
        
        if (confirmed) {
          try {
            const result = await api.deleteCompany(id, true); // Force delete
            await loadCompanies();
            
            // Show success message with details
            const { deleted_records } = result;
            const details = [];
            if (deleted_records.purchases > 0) details.push(`${deleted_records.purchases} записа от дневника на покупките`);
            if (deleted_records.sales > 0) details.push(`${deleted_records.sales} записа от дневника за продажбите`); 
            if (deleted_records.declarations > 0) details.push(`${deleted_records.declarations} ДДС декларации`);
            
            alert(
              `Фирмата "${company.name}" беше изтрита успешно!\n\n` +
              (details.length > 0 ? `Изтрити данни:\n• ${details.join('\n• ')}` : '')
            );
          } catch (forceError) {
            let forceErrorMsg = 'Грешка при принудително изтриване';
            if (forceError instanceof Error) {
              try {
                const forceErrorData = JSON.parse(forceError.message);
                forceErrorMsg = forceErrorData.detail || forceError.message;
              } catch {
                forceErrorMsg = forceError.message;
              }
            }
            error = forceErrorMsg;
          }
        }
      } else {
        error = errorMsg;
      }
    }
  }
</script>

<svelte:head>
  <title>Служебни функции - VAT System</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="mb-8 flex items-center justify-between">
    <div class="flex items-center">
      <a 
        href="/" 
        class="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        title="Към началната страница"
      >
        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      </a>
      <div>
        <div class="flex items-center text-sm text-gray-500 mb-1">
          <a href="/" class="hover:text-gray-700">Начало</a>
          <span class="mx-2">›</span>
          <span class="text-gray-900">Служебни функции</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">Служебни функции</h1>
        <p class="mt-2 text-gray-600">
          Избор и управление на задължени лица за ДДС отчетност
        </p>
      </div>
    </div>
    
    <a
      href="/companies/new"
      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
    >
      <Plus class="h-4 w-4 mr-2" />
      Нова фирма
    </a>
  </div>

  <!-- Error Message -->
  {#if error}
    <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
      <div class="flex items-center">
        <AlertCircle class="h-5 w-5 text-red-500 mr-2" />
        <p class="text-red-700">{error}</p>
      </div>
    </div>
  {/if}

  <!-- Companies List -->
  {#if loading}
    <div class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Зареждане...</p>
    </div>
  {:else if companies.length === 0}
    <div class="text-center py-12">
      <Building2 class="h-16 w-16 text-gray-400 mx-auto mb-4" />
      <h3 class="text-xl font-medium text-gray-900 mb-2">Няма регистрирани фирми</h3>
      <p class="text-gray-500 mb-6">
        Започнете с регистриране на първата си фирма за ДДС отчетност
      </p>
      <a
        href="/companies/new"
        class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
      >
        <Plus class="h-5 w-5 mr-2" />
        Добави първата фирма
      </a>
    </div>
  {:else}
    <div class="bg-white rounded-lg shadow-sm overflow-hidden">
      <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">
          Регистрирани фирми ({companies.length})
        </h3>
      </div>
      
      <div class="divide-y divide-gray-200">
        {#each companies as company}
          <div class="px-6 py-4 flex items-center justify-between hover:bg-gray-50">
            <div class="flex-1">
              <h4 class="text-lg font-medium text-gray-900">{company.name}</h4>
              <div class="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                <span>ЕИК: {company.uic}</span>
                <span>ДДС: {company.vat_number}</span>
                <span>Адрес: {company.address}</span>
              </div>
              <div class="mt-2 flex items-center space-x-4">
                {#if company.is_active}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Активна
                  </span>
                {/if}
                <span class="text-xs text-gray-400">
                  Създадена: {new Date(company.created_at).toLocaleDateString('bg-BG')}
                </span>
              </div>
            </div>
            
            <div class="flex items-center space-x-2">
              <a
                href="/companies/{company.id}/reports"
                class="p-2 text-gray-400 hover:text-green-600"
                title="Справки и отчети"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </a>
              <a
                href="/companies/{company.id}/edit"
                class="p-2 text-gray-400 hover:text-blue-600"
                title="Редактирай"
              >
                <Edit class="h-4 w-4" />
              </a>
              <button
                on:click={() => deleteCompany(company.id)}
                class="p-2 text-gray-400 hover:text-red-600"
                title="Изтрий"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Instructions -->
  <div class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
    <h3 class="text-lg font-medium text-blue-900 mb-4">Инструкции</h3>
    <ul class="text-sm text-blue-800 space-y-2">
      <li>• За да започнете работа с ДДС отчетност, първо трябва да регистрирате фирмата си</li>
      <li>• ЕИК (Единен идентификационен код) се проверява автоматично за валидност</li>
      <li>• ДДС номерът трябва да започва с "BG" последван от ЕИК</li>
      <li>• Активните фирми могат да генерират ДДС декларации и дневници</li>
    </ul>
  </div>
</div>