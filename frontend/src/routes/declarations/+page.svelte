<script lang="ts">
  import { onMount } from 'svelte';
  import { Calculator, FileText, Send, AlertCircle, Building2, Calendar, CheckCircle, Clock, CreditCard, Download, Package, RotateCcw, Trash2 } from 'lucide-svelte';
  import { api, VATValidator, type Company, type VATDeclaration } from '$lib/api';
  
  let companies: Company[] = [];
  let selectedCompany: Company | null = null;
  let currentPeriod = getCurrentPeriod();
  let declaration: VATDeclaration | null = null;
  let loading = false;
  let error = '';
  let generating = false;
  let submitting = false;
  let exporting = false;
  let reverting = false;
  let deleting = false;
  
  function getCurrentPeriod(): string {
    const now = new Date();
    return `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}`;
  }
  
  onMount(async () => {
    await loadCompanies();
  });
  
  async function loadCompanies() {
    try {
      companies = await api.listCompanies();
      if (companies.length === 1) {
        selectedCompany = companies[0];
        await loadDeclaration();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането';
    }
  }
  
  async function loadDeclaration() {
    if (!selectedCompany || !currentPeriod) return;
    
    loading = true;
    error = '';
    
    try {
      declaration = await api.getDeclaration(selectedCompany.uic, currentPeriod);
    } catch (e) {
      // Declaration doesn't exist yet - this is normal
      declaration = null;
    } finally {
      loading = false;
    }
  }
  
  async function generateDeclaration() {
    if (!selectedCompany || !currentPeriod) return;
    
    generating = true;
    error = '';
    
    try {
      declaration = await api.generateDeclaration(selectedCompany.uic, currentPeriod);
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при генериране');
    } finally {
      generating = false;
    }
  }
  
  async function submitDeclaration() {
    if (!declaration) return;
    
    submitting = true;
    error = '';
    
    try {
      await api.submitDeclaration(declaration.id);
      await loadDeclaration(); // Reload to get updated status
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при подаване');
    } finally {
      submitting = false;
    }
  }
  
  async function revertDeclaration() {
    if (!declaration) return;
    
    if (!confirm('Сигурни ли сте, че искате да върнете декларацията в чернова? Това ще отмени подаването ѝ в НАП.')) {
      return;
    }
    
    reverting = true;
    error = '';
    
    try {
      await api.revertDeclaration(declaration.id);
      await loadDeclaration(); // Reload to get updated status
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при връщане в чернова');
    } finally {
      reverting = false;
    }
  }
  
  async function deleteDeclaration() {
    if (!declaration) return;
    
    if (!confirm('Сигурни ли сте, че искате да изтриете декларацията? Това действие е необратимо.')) {
      return;
    }
    
    deleting = true;
    error = '';
    
    try {
      await api.deleteDeclaration(declaration.id);
      declaration = null; // Clear the declaration from view
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при изтриване');
    } finally {
      deleting = false;
    }
  }
  
  function formatCurrency(amount: number): string {
    return VATValidator.formatCurrency(amount);
  }
  
  function getStatusLabel(status: string): { label: string; color: string; icon: any } {
    switch (status) {
      case 'DRAFT':
        return { label: 'Чернова', color: 'text-gray-600 bg-gray-100', icon: FileText };
      case 'SUBMITTED':
        return { label: 'Подадена', color: 'text-blue-600 bg-blue-100', icon: Send };
      case 'PAID':
        return { label: 'Платена', color: 'text-green-600 bg-green-100', icon: CheckCircle };
      default:
        return { label: status, color: 'text-gray-600 bg-gray-100', icon: Clock };
    }
  }
  
  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('bg-BG');
  }
  
  function isNullDeclaration(): boolean {
    if (!declaration) return false;
    return declaration.field_50 === 0 && declaration.field_60 === 0 && declaration.field_80 === 0;
  }
  
  async function downloadExport(format: 'xml' | 'json' | 'package') {
    if (!declaration) return;
    
    exporting = true;
    error = '';
    
    try {
      const url = `http://localhost:8000/api/declarations/${declaration.id}/export/${format}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `declaration_${currentPeriod}.${format}`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при експорт');
    } finally {
      exporting = false;
    }
  }
  
  $: if (selectedCompany) {
    loadDeclaration();
  }
</script>

<svelte:head>
  <title>Справка-декларация по ЗДДС - VAT System</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
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
          <span class="text-gray-900">Декларации</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">Справка-декларация по ЗДДС и VIES</h1>
        <p class="mt-2 text-gray-600">
          Генериране и подаване на месечни ДДС декларации към НАП
        </p>
      </div>
    </div>
  </div>
  
  <!-- Company and Period Selection -->
  <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label for="company-select" class="block text-sm font-medium text-gray-700 mb-2">Фирма</label>
        <select 
          id="company-select"
          bind:value={selectedCompany}
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        >
          <option value={null}>Изберете фирма</option>
          {#each companies as company}
            <option value={company}>{company.name} ({company.uic})</option>
          {/each}
        </select>
      </div>
      
      <div>
        <label for="period-input" class="block text-sm font-medium text-gray-700 mb-2">Период</label>
        <input
          id="period-input"
          type="text"
          bind:value={currentPeriod}
          placeholder="YYYYMM"
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          on:change={loadDeclaration}
        />
        <p class="mt-1 text-xs text-gray-500">Формат: YYYYMM (напр. 202103)</p>
      </div>
      
      <div class="flex items-end">
        <button
          on:click={loadDeclaration}
          disabled={!selectedCompany || loading}
          class="w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 disabled:opacity-50"
        >
          <Calendar class="h-4 w-4 inline mr-2" />
          {loading ? 'Зареждане...' : 'Зареди период'}
        </button>
      </div>
    </div>
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
  
  <!-- Instructions for null declarations -->
  <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
    <h3 class="text-sm font-medium text-blue-900 mb-2">Инструкции за декларации:</h3>
    <ul class="text-sm text-blue-800 space-y-1">
      <li>• При <strong>нулева декларация</strong> се попълва само периода - не се въвежда нищо друго</li>
      <li>• При <strong>редовна декларация</strong> се натиска [Декларация ДДС] и формата се попълва автоматично</li>
      <li>• Срокът за подаване е до <strong>14-то число</strong> на следващия месец</li>
      <li>• За възстановяване на ДДС попълнете клетка 80</li>
    </ul>
  </div>
  
  {#if !selectedCompany}
    <div class="text-center py-12">
      <Building2 class="h-12 w-12 text-gray-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-gray-900">Изберете фирма</h3>
      <p class="text-gray-500">Изберете фирма от падащото меню за да започнете</p>
    </div>
  {:else}
    <!-- Declaration Content -->
    {#if !declaration}
      <div class="bg-white rounded-lg shadow-sm p-8">
        <div class="text-center">
          <Calculator class="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 class="text-xl font-medium text-gray-900 mb-2">
            Декларация за {currentPeriod}
          </h3>
          <p class="text-gray-500 mb-6">
            Няма генерирана декларация за този период
          </p>
          
          <button
            on:click={generateDeclaration}
            disabled={generating}
            class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {#if generating}
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Генериране...
            {:else}
              <Calculator class="h-5 w-5 mr-2" />
              Декларация ДДС
            {/if}
          </button>
        </div>
      </div>
    {:else}
      <!-- Declaration Details -->
      <div class="bg-white rounded-lg shadow-sm overflow-hidden">
        <!-- Header -->
        <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-medium text-gray-900">
                Справка-декларация {currentPeriod}
              </h3>
              <p class="text-sm text-gray-600">
                {selectedCompany.name} (ДДС: {selectedCompany.vat_number})
              </p>
            </div>
            
            <div class="flex items-center space-x-2">
              {#if declaration}
                {@const status = getStatusLabel(declaration.status)}
                <svelte:component this={status.icon} class="h-4 w-4" />
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium {status.color}">
                  {status.label}
                </span>
              {/if}
            </div>
          </div>
        </div>
        
        <!-- Declaration Form Fields -->
        <div class="p-6">
          {#if isNullDeclaration()}
            <div class="text-center py-8">
              <CheckCircle class="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-gray-900 mb-2">Нулева декларация</h3>
              <p class="text-gray-600">
                Няма обороти за периода - декларацията е готова за подаване
              </p>
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Sales VAT (Field 50) -->
              <div class="bg-blue-50 rounded-lg p-4">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-blue-900">Клетка 50</h4>
                    <p class="text-xs text-blue-700">ДДС от продажби</p>
                  </div>
                  <div class="text-right">
                    <p class="text-lg font-bold text-blue-900">
                      {formatCurrency(declaration.field_50)}
                    </p>
                  </div>
                </div>
              </div>
              
              <!-- Purchase VAT (Field 60) -->
              <div class="bg-green-50 rounded-lg p-4">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-green-900">Клетка 60</h4>
                    <p class="text-xs text-green-700">ДДС от покупки</p>
                  </div>
                  <div class="text-right">
                    <p class="text-lg font-bold text-green-900">
                      {formatCurrency(declaration.field_60)}
                    </p>
                  </div>
                </div>
              </div>
              
              <!-- Refund (Field 80) -->
              {#if declaration.field_80 > 0}
                <div class="bg-purple-50 rounded-lg p-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-medium text-purple-900">Клетка 80</h4>
                      <p class="text-xs text-purple-700">Възстановяване на ДДС</p>
                    </div>
                    <div class="text-right">
                      <p class="text-lg font-bold text-purple-900">
                        {formatCurrency(declaration.field_80)}
                      </p>
                    </div>
                  </div>
                </div>
              {/if}
              
              <!-- Payment Due or Refund -->
              {#if declaration.payment_due > 0}
                <div class="bg-orange-50 rounded-lg p-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-medium text-orange-900">За доплащане</h4>
                      <p class="text-xs text-orange-700">Срок: до {formatDate(declaration.payment_deadline || '')}</p>
                    </div>
                    <div class="text-right">
                      <p class="text-xl font-bold text-orange-900">
                        {formatCurrency(declaration.payment_due)}
                      </p>
                    </div>
                  </div>
                </div>
              {:else if declaration.refund_due > 0}
                <div class="bg-green-50 rounded-lg p-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-medium text-green-900">За възстановяване</h4>
                      <p class="text-xs text-green-700">Заявка за връщане на ДДС</p>
                    </div>
                    <div class="text-right">
                      <p class="text-xl font-bold text-green-900">
                        {formatCurrency(declaration.refund_due)}
                      </p>
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          {/if}
          
          <!-- Submission Info -->
          {#if declaration.submission_date}
            <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div class="flex items-center">
                <Send class="h-5 w-5 text-blue-500 mr-3" />
                <div>
                  <h4 class="text-sm font-medium text-blue-900">Подадена в НАП</h4>
                  <p class="text-xs text-blue-700">
                    Дата: {formatDate(declaration.submission_date)}
                    {#if declaration.nap_submission_id}
                      | Референтен номер: {declaration.nap_submission_id}
                    {/if}
                  </p>
                </div>
              </div>
            </div>
          {/if}
        </div>
        
        <!-- Actions -->
        <div class="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <div class="flex justify-between items-center">
            <div class="text-sm text-gray-600">
              Създадена: {formatDate(declaration.created_at)}
            </div>
            
            <div class="flex flex-col space-y-3">
              <!-- Export buttons row -->
              <div class="flex space-x-2">
                <button
                  on:click={() => downloadExport('xml')}
                  disabled={exporting}
                  class="inline-flex items-center px-3 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 disabled:opacity-50"
                  title="Изтегли XML файл за НАП"
                >
                  {#if exporting}
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700 mr-1"></div>
                  {:else}
                    <FileText class="h-4 w-4 mr-1" />
                  {/if}
                  XML
                </button>
                
                <button
                  on:click={() => downloadExport('json')}
                  disabled={exporting}
                  class="inline-flex items-center px-3 py-2 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 disabled:opacity-50"
                  title="Изтегли JSON файл"
                >
                  {#if exporting}
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-green-700 mr-1"></div>
                  {:else}
                    <Download class="h-4 w-4 mr-1" />
                  {/if}
                  JSON
                </button>
                
                <button
                  on:click={() => downloadExport('package')}
                  disabled={exporting}
                  class="inline-flex items-center px-3 py-2 border border-purple-300 text-sm font-medium rounded-md text-purple-700 bg-purple-50 hover:bg-purple-100 disabled:opacity-50"
                  title="Изтегли пълен пакет с всички документи"
                >
                  {#if exporting}
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-700 mr-1"></div>
                  {:else}
                    <Package class="h-4 w-4 mr-1" />
                  {/if}
                  Пакет
                </button>
              </div>
              
              <!-- Action buttons row -->
              <div class="flex space-x-3">
                {#if declaration.status === 'DRAFT'}
                  <button
                    on:click={submitDeclaration}
                    disabled={submitting}
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                  >
                    {#if submitting}
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Подаване...
                    {:else}
                      <Send class="h-4 w-4 mr-2" />
                      Подай в НАП
                    {/if}
                  </button>
                {/if}
                
                {#if declaration.status === 'SUBMITTED'}
                  <button
                    on:click={revertDeclaration}
                    disabled={reverting}
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50"
                    title="Върни в чернова за редактиране"
                  >
                    {#if reverting}
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Връщане...
                    {:else}
                      <RotateCcw class="h-4 w-4 mr-2" />
                      Върни в чернова
                    {/if}
                  </button>
                {/if}
                
                {#if declaration.payment_due > 0 && declaration.status === 'SUBMITTED'}
                  <button
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-orange-600 hover:bg-orange-700"
                  >
                    <CreditCard class="h-4 w-4 mr-2" />
                    Плати ДДС
                  </button>
                {/if}
                
                {#if declaration.status === 'DRAFT'}
                  <button
                    on:click={deleteDeclaration}
                    disabled={deleting}
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                    title="Изтрий декларация"
                  >
                    {#if deleting}
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Изтриване...
                    {:else}
                      <Trash2 class="h-4 w-4 mr-2" />
                      Изтрий
                    {/if}
                  </button>
                {/if}
                
                <button
                  on:click={generateDeclaration}
                  disabled={generating}
                  class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Calculator class="h-4 w-4 mr-2" />
                  Регенерирай
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>