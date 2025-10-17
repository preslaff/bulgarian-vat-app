<script lang="ts">
  import { onMount } from 'svelte';
  import { FileText, Download, Globe, TrendingUp, AlertCircle, Calendar, Building2 } from 'lucide-svelte';
  import { api, VATValidator, type Company } from '$lib/api';
  
  let companies: Company[] = [];
  let selectedCompany: Company | null = null;
  let selectedPeriod: string = getCurrentPeriod();
  let loading = false;
  let error = '';
  let generating = false;
  
  let viesData: any = null;
  let showViesDetails = false;
  
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
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането на фирмите';
    }
  }
  
  async function generateVIESDeclaration() {
    if (!selectedCompany || !selectedPeriod) return;
    
    generating = true;
    error = '';
    
    try {
      const response = await fetch(`http://localhost:8000/api/companies/${selectedCompany.uic}/vies/${selectedPeriod}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Грешка при генериране на VIES декларация');
      }
      
      viesData = await response.json();
      showViesDetails = true;
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при генериране на VIES декларация');
    } finally {
      generating = false;
    }
  }
  
  async function downloadVIESXML() {
    if (!selectedCompany || !selectedPeriod) return;
    
    try {
      const url = `http://localhost:8000/api/companies/${selectedCompany.uic}/vies/${selectedPeriod}/export`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Грешка при експорт на VIES декларация');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `VIES_Declaration_${selectedPeriod}.xml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при експорт');
    }
  }
  
  async function downloadReportingProtocol() {
    if (!selectedCompany || !selectedPeriod) return;
    
    try {
      const url = `http://localhost:8000/api/companies/${selectedCompany.uic}/reporting-protocol/${selectedPeriod}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Грешка при генериране на справка-протокол');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `Reporting_Protocol_${selectedPeriod}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при експорт');
    }
  }
</script>

<svelte:head>
  <title>Отчети и VIES - VAT System</title>
</svelte:head>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Отчети и VIES декларации</h1>
        <p class="mt-2 text-gray-600">
          Генериране на справки-протоколи и VIES декларации за ЕС операции
        </p>
      </div>
      
      <div class="flex items-center space-x-2 text-sm text-gray-500">
        <Globe class="h-4 w-4" />
        <span>EU VAT Reporting</span>
      </div>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white shadow rounded-lg p-6 mb-8">
    <h3 class="text-lg font-medium text-gray-900 mb-4">Параметри на отчета</h3>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Company Selection -->
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

      <!-- Period Selection -->
      <div>
        <label for="period-select" class="block text-sm font-medium text-gray-700 mb-2">Период (YYYYMM)</label>
        <input
          type="text"
          id="period-select"
          bind:value={selectedPeriod}
          placeholder="202401"
          pattern="[0-9]{6}"
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        />
        <p class="mt-1 text-sm text-gray-500">
          Формат: YYYYMM (например: 202401 за януари 2024)
        </p>
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

  <!-- Action Cards -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
    
    <!-- VIES Declaration Card -->
    <div class="bg-white shadow rounded-lg overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200 bg-blue-50">
        <div class="flex items-center">
          <Globe class="h-6 w-6 text-blue-600 mr-3" />
          <div>
            <h3 class="text-lg font-medium text-gray-900">VIES Декларация</h3>
            <p class="text-sm text-gray-600">Декларация за вътрешно-общностни операции</p>
          </div>
        </div>
      </div>
      
      <div class="p-6">
        <p class="text-gray-600 mb-4">
          Генерира VIES декларация за операции с ЕС контрагенти съгласно изискванията 
          на европейската система за обмен на информация по ДДС.
        </p>
        
        <div class="flex space-x-3">
          <button
            on:click={generateVIESDeclaration}
            disabled={!selectedCompany || !selectedPeriod || generating}
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {#if generating}
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Генерира...
            {:else}
              <TrendingUp class="h-4 w-4 mr-2" />
              Генерирай VIES
            {/if}
          </button>
          
          {#if viesData}
            <button
              on:click={downloadVIESXML}
              class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download class="h-4 w-4 mr-2" />
              Изтегли XML
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Reporting Protocol Card -->
    <div class="bg-white shadow rounded-lg overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200 bg-green-50">
        <div class="flex items-center">
          <FileText class="h-6 w-6 text-green-600 mr-3" />
          <div>
            <h3 class="text-lg font-medium text-gray-900">Справка-протокол</h3>
            <p class="text-sm text-gray-600">Детайлна справка с всички данни</p>
          </div>
        </div>
      </div>
      
      <div class="p-6">
        <p class="text-gray-600 mb-4">
          Генерира подробна справка-протокол с всички записи от дневниците 
          за продажби и покупки, включително валидация на данните.
        </p>
        
        <button
          on:click={downloadReportingProtocol}
          disabled={!selectedCompany || !selectedPeriod}
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
        >
          <Download class="h-4 w-4 mr-2" />
          Генерирай протокол
        </button>
      </div>
    </div>
  </div>

  <!-- VIES Details -->
  {#if showViesDetails && viesData}
    <div class="bg-white shadow rounded-lg p-6 mb-8">
      <h3 class="text-lg font-medium text-gray-900 mb-4">VIES Декларация - Резултати</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-blue-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-blue-900">
            {viesData.total_supplies} лв.
          </div>
          <div class="text-sm text-blue-600">Общо доставки към ЕС</div>
        </div>
        
        <div class="bg-green-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-green-900">
            {viesData.total_acquisitions} лв.
          </div>
          <div class="text-sm text-green-600">Общо придобивания от ЕС</div>
        </div>
        
        <div class="bg-purple-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-purple-900">
            {viesData.eu_partners}
          </div>
          <div class="text-sm text-purple-600">Брой ЕС контрагенти</div>
        </div>
      </div>
      
      <div class="mt-4 p-4 bg-gray-50 rounded-lg">
        <p class="text-sm text-gray-600">
          <strong>Период:</strong> {viesData.period} | 
          <strong>Фирма:</strong> {viesData.company_uic} | 
          <strong>Генерирана:</strong> {new Date(viesData.created_at).toLocaleDateString('bg-BG')}
        </p>
      </div>
    </div>
  {/if}

  <!-- Information Panel -->
  <div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
    <h3 class="text-lg font-medium text-blue-900 mb-4">Информация за отчетите</h3>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <h4 class="font-medium text-blue-900 mb-2">VIES Декларация</h4>
        <ul class="text-sm text-blue-800 space-y-1">
          <li>• Задължителна за фирми с ЕС операции</li>
          <li>• Подава се ежемесечно в НАП</li>
          <li>• XML формат за електронно подаване</li>
          <li>• Включва доставки и придобивания</li>
        </ul>
      </div>
      
      <div>
        <h4 class="font-medium text-blue-900 mb-2">Справка-протокол</h4>
        <ul class="text-sm text-blue-800 space-y-1">
          <li>• Детайлна справка за контрол</li>
          <li>• Включва всички полета на декларацията</li>
          <li>• Валидация на въведените данни</li>
          <li>• Подходяща за архивиране</li>
        </ul>
      </div>
    </div>
  </div>
</div>