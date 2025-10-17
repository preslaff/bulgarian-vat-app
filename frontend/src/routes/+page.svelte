<script lang="ts">
  import { onMount } from 'svelte';
  import { Building2, FileText, Calculator, Send, TrendingUp, AlertCircle } from 'lucide-svelte';
  import { api, type Company, type VATDeclaration } from '$lib/api';
  
  let companies: Company[] = [];
  let recentDeclarations: VATDeclaration[] = [];
  let loading = true;
  let error = '';

  const quickActions = [
    {
      title: 'Нова фирма',
      description: 'Регистриране на задължено лице',
      icon: Building2,
      href: '/companies/new',
      color: 'bg-blue-500'
    },
    {
      title: 'Покупки',
      description: 'Дневник на покупките',
      icon: FileText, 
      href: '/journals/purchases',
      color: 'bg-green-500'
    },
    {
      title: 'Продажби', 
      description: 'Дневник за продажбите',
      icon: TrendingUp,
      href: '/journals/sales',
      color: 'bg-purple-500'
    },
    {
      title: 'Декларация',
      description: 'Справка-декларация по ЗДДС',
      icon: Calculator,
      href: '/declarations',
      color: 'bg-orange-500'
    }
  ];

  onMount(async () => {
    try {
      // Load dashboard data
      companies = await api.listCompanies();
      // TODO: Load recent declarations
      loading = false;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането';
      loading = false;
    }
  });

  function getCurrentPeriod(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    return `${year}${month.toString().padStart(2, '0')}`;
  }
</script>

<svelte:head>
  <title>Начало - Дневници VAT System</title>
</svelte:head>

<div class="max-w-7xl mx-auto">
  <!-- Welcome section -->
  <div class="bg-white rounded-lg shadow-sm p-6 mb-8">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold text-gray-900">Добре дошли в Дневници</h2>
        <p class="mt-2 text-gray-600">
          Модерна система за управление на ДДС декларации, базирана на НАП Дневници v14.02
        </p>
      </div>
      <div class="text-right">
        <p class="text-sm text-gray-500">Текущ период</p>
        <p class="text-2xl font-bold text-blue-600">{getCurrentPeriod()}</p>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Зареждане...</p>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
      <div class="flex items-center">
        <AlertCircle class="h-5 w-5 text-red-500 mr-2" />
        <p class="text-red-700">{error}</p>
      </div>
    </div>
  {:else}
    <!-- Quick actions -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {#each quickActions as action}
        <a
          href={action.href}
          class="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow group"
        >
          <div class="flex items-center">
            <div class="{action.color} rounded-lg p-3 text-white group-hover:scale-110 transition-transform">
              <svelte:component this={action.icon} class="h-6 w-6" />
            </div>
            <div class="ml-4">
              <h3 class="text-lg font-medium text-gray-900">{action.title}</h3>
              <p class="text-sm text-gray-500">{action.description}</p>
            </div>
          </div>
        </a>
      {/each}
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Companies overview -->
      <div class="bg-white rounded-lg shadow-sm p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Регистрирани фирми</h3>
        
        {#if companies.length === 0}
          <div class="text-center py-8">
            <Building2 class="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p class="text-gray-500">Няма регистрирани фирми</p>
            <a 
              href="/companies/new"
              class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Добави първата фирма
            </a>
          </div>
        {:else}
          <div class="space-y-3">
            {#each companies.slice(0, 5) as company}
              <div class="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                <div>
                  <h4 class="font-medium text-gray-900">{company.name}</h4>
                  <p class="text-sm text-gray-500">УИК: {company.uic} | ДДС: {company.vat_number}</p>
                </div>
                <div class="flex items-center space-x-2">
                  {#if company.is_active}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Активна
                    </span>
                  {/if}
                </div>
              </div>
            {/each}
            
            {#if companies.length > 5}
              <a 
                href="/companies"
                class="block text-center py-2 text-sm text-blue-600 hover:text-blue-700"
              >
                Виж всички ({companies.length})
              </a>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Recent activity -->
      <div class="bg-white rounded-lg shadow-sm p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Последна активност</h3>
        
        <div class="space-y-3">
          <div class="flex items-center p-3 border border-gray-200 rounded-lg">
            <Calculator class="h-8 w-8 text-blue-500 mr-3" />
            <div>
              <h4 class="font-medium text-gray-900">Система стартирана</h4>
              <p class="text-sm text-gray-500">API сървър е достъпен на порт 8000</p>
            </div>
          </div>
          
          <div class="flex items-center p-3 border border-gray-200 rounded-lg">
            <FileText class="h-8 w-8 text-green-500 mr-3" />
            <div>
              <h4 class="font-medium text-gray-900">Готово за употреба</h4>
              <p class="text-sm text-gray-500">Всички функционалности са налични</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Key features info -->
    <div class="mt-8 bg-blue-50 rounded-lg p-6">
      <h3 class="text-lg font-medium text-blue-900 mb-4">Ключови функционалности</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div class="flex items-start">
          <Building2 class="h-5 w-5 text-blue-600 mt-0.5 mr-2" />
          <div>
            <h4 class="font-medium text-blue-900">Управление на фирми</h4>
            <p class="text-sm text-blue-700">Регистриране и управление на задължени лица</p>
          </div>
        </div>
        
        <div class="flex items-start">
          <FileText class="h-5 w-5 text-blue-600 mt-0.5 mr-2" />
          <div>
            <h4 class="font-medium text-blue-900">Дневници</h4>
            <p class="text-sm text-blue-700">Покупки и продажби с автоматично изчисляване на ДДС</p>
          </div>
        </div>
        
        <div class="flex items-start">
          <Calculator class="h-5 w-5 text-blue-600 mt-0.5 mr-2" />
          <div>
            <h4 class="font-medium text-blue-900">Декларации</h4>
            <p class="text-sm text-blue-700">Автоматично генериране на справки-декларации</p>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>