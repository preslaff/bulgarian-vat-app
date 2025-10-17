<script lang="ts">
  import { onMount } from 'svelte';
  import { FileText, TrendingUp, Plus, Calendar, Building2, AlertCircle } from 'lucide-svelte';
  import { api, type Company } from '$lib/api';
  
  let companies: Company[] = [];
  let loading = true;
  let error = '';
  
  const journalTypes = [
    {
      title: 'Дневник на покупките',
      description: 'Регистриране на входящи фактури и ДДС кредит',
      icon: FileText,
      href: '/journals/purchases',
      color: 'bg-green-500',
      count: 0 // TODO: Load actual counts
    },
    {
      title: 'Дневник за продажбите', 
      description: 'Регистриране на изходящи фактури и ДДС дебит',
      icon: TrendingUp,
      href: '/journals/sales',
      color: 'bg-purple-500',
      count: 0 // TODO: Load actual counts
    }
  ];

  onMount(async () => {
    try {
      companies = await api.listCompanies();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането';
    } finally {
      loading = false;
    }
  });

  function getCurrentPeriod(): string {
    const now = new Date();
    return `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}`;
  }
</script>

<svelte:head>
  <title>Въвеждане - VAT System</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-gray-900">Въвеждане</h1>
    <p class="mt-2 text-gray-600">
      Дневници на покупките и продажбите за период {getCurrentPeriod()}
    </p>
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

  {#if loading}
    <div class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Зареждане...</p>
    </div>
  {:else if companies.length === 0}
    <!-- No companies message -->
    <div class="text-center py-12">
      <Building2 class="h-16 w-16 text-gray-400 mx-auto mb-4" />
      <h3 class="text-xl font-medium text-gray-900 mb-2">Няма регистрирани фирми</h3>
      <p class="text-gray-500 mb-6">
        За да започнете въвеждане на дневници, първо трябва да регистрирате фирма
      </p>
      <a
        href="/companies/new"
        class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
      >
        <Plus class="h-5 w-5 mr-2" />
        Регистрирай фирма
      </a>
    </div>
  {:else}
    <!-- Journal Types -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {#each journalTypes as journal}
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
          <div class="p-6">
            <div class="flex items-center mb-4">
              <div class="{journal.color} rounded-lg p-3 text-white mr-4">
                <svelte:component this={journal.icon} class="h-6 w-6" />
              </div>
              <div>
                <h3 class="text-lg font-medium text-gray-900">{journal.title}</h3>
                <p class="text-sm text-gray-500">{journal.description}</p>
              </div>
            </div>
            
            <div class="mb-6">
              <div class="text-2xl font-bold text-gray-900">{journal.count}</div>
              <div class="text-sm text-gray-500">записа за текущия период</div>
            </div>
            
            <a
              href={journal.href}
              class="block w-full text-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white {journal.color} hover:opacity-90"
            >
              <Plus class="h-4 w-4 inline mr-2" />
              Нов запис
            </a>
          </div>
        </div>
      {/each}
    </div>

    <!-- Active Companies -->
    <div class="bg-white rounded-lg shadow-sm">
      <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Активни фирми</h3>
      </div>
      
      <div class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each companies.filter(c => c.is_active) as company}
            <div class="border border-gray-200 rounded-lg p-4">
              <h4 class="font-medium text-gray-900">{company.name}</h4>
              <p class="text-sm text-gray-500 mt-1">
                УИК: {company.uic} | ДДС: {company.vat_number}
              </p>
              <div class="mt-3 flex space-x-2">
                <a
                  href="/journals/purchases?company={company.id}"
                  class="text-xs px-2 py-1 bg-green-100 text-green-800 rounded"
                >
                  Покупки
                </a>
                <a
                  href="/journals/sales?company={company.id}"
                  class="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded"
                >
                  Продажби
                </a>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Instructions -->
    <div class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
      <h3 class="text-lg font-medium text-blue-900 mb-4">Инструкции за въвеждане</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 class="font-medium text-blue-900 mb-2">Дневник на покупките</h4>
          <ul class="text-sm text-blue-800 space-y-1">
            <li>• Въвеждат се всички входящи фактури</li>
            <li>• ДДС се изчислява автоматично</li>
            <li>• Поддържат се кредитни известия</li>
            <li>• Валидация на номера и дати</li>
          </ul>
        </div>
        <div>
          <h4 class="font-medium text-blue-900 mb-2">Дневник за продажбите</h4>
          <ul class="text-sm text-blue-800 space-y-1">
            <li>• Въвеждат се всички изходящи фактури</li>
            <li>• Автоматично изчисляване на ДДС дебит</li>
            <li>• Поддържат се сторно операции</li>
            <li>• Експорт за външна търговия</li>
          </ul>
        </div>
      </div>
    </div>
  {/if}
</div>