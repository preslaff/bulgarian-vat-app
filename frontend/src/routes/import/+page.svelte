<script lang="ts">
  import { onMount } from 'svelte';
  import { Upload, FileText, CheckCircle, AlertCircle, Eye, Download, Building2 } from 'lucide-svelte';
  import { api, type Company } from '$lib/api';
  
  let companies: Company[] = [];
  let selectedCompany: Company | null = null;
  let selectedJournalType: string = 'purchase';
  let uploadedFile: File | null = null;
  let uploadProgress = 0;
  let isUploading = false;
  let processingResult: any = null;
  let previewData: any = null;
  let error = '';
  let showPreview = false;

  const journalTypes = [
    { value: 'purchase', label: 'Дневник на покупките', description: 'Входящи фактури от доставчици' },
    { value: 'sales', label: 'Дневник за продажбите', description: 'Изходящи фактури към клиенти' }
  ];

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

  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      uploadedFile = input.files[0];
      
      // Validate file type
      const allowedTypes = ['.xlsx', '.xls', '.json'];
      const fileExtension = uploadedFile.name.toLowerCase().slice(uploadedFile.name.lastIndexOf('.'));
      
      if (!allowedTypes.includes(fileExtension)) {
        error = 'Моля изберете Excel (.xlsx, .xls) или JSON файл';
        uploadedFile = null;
        return;
      }
      
      error = '';
    }
  }

  async function processFile() {
    if (!uploadedFile || !selectedCompany) {
      error = 'Моля изберете файл и фирма';
      return;
    }

    isUploading = true;
    uploadProgress = 0;
    error = '';

    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);
      formData.append('company_uic', selectedCompany.uic);
      formData.append('journal_type', selectedJournalType);

      const endpoint = uploadedFile.name.endsWith('.json') ? 
        'http://localhost:8000/api/vat/import-json' : 
        'http://localhost:8000/api/vat/import-excel';

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        uploadProgress = Math.min(uploadProgress + 10, 90);
      }, 200);

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);
      uploadProgress = 100;

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Грешка при обработката на файла');
      }

      const result = await response.json();
      processingResult = result;
      
      // Show preview of first few entries
      if (result.data && result.data.preview_data) {
        previewData = result.data.preview_data.slice(0, 10);
      }
      
      // Display import messages to user
      if (result.data && result.data.import_messages) {
        console.log('Import messages:', result.data.import_messages);
        
        // Show warnings/errors if present
        if (result.data.has_errors || result.data.has_warnings) {
          const errorCount = result.data.import_messages.filter(msg => msg.includes('❌')).length;
          const warningCount = result.data.import_messages.filter(msg => msg.includes('⚠️')).length;
          
          if (errorCount > 0) {
            console.warn(`Found ${errorCount} errors in import`);
          }
          if (warningCount > 0) {
            console.warn(`Found ${warningCount} warnings in import`);
          }
        }
      }

    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при обработката';
      processingResult = null;
    } finally {
      isUploading = false;
    }
  }

  async function importEntries(autoApprove: boolean = false) {
    if (!processingResult || !processingResult.data || !processingResult.data.preview_data) {
      error = 'Няма данни за импортиране';
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/vat/validate-import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          entries: processingResult.data.preview_data,
          auto_approve: autoApprove
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Грешка при импортирането');
      }

      const result = await response.json();
      
      if (autoApprove && result.status === 'success') {
        processingResult = {
          ...processingResult,
          imported: true,
          importResult: result
        };
      } else {
        processingResult = {
          ...processingResult,
          validated: true,
          validationResult: result
        };
      }

    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при импортирането';
    }
  }

  function resetUpload() {
    uploadedFile = null;
    uploadProgress = 0;
    processingResult = null;
    previewData = null;
    error = '';
    showPreview = false;
    
    // Reset file input
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(amount);
  }

  async function downloadTemplate(journalType: string = 'purchase') {
    try {
      const response = await fetch(`http://localhost:8000/api/vat/download-template?journal_type=${journalType}`);
      
      if (!response.ok) {
        throw new Error('Грешка при генериране на шаблона');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `VAT_${journalType}_template.xlsx`;
      
      document.body.appendChild(a);
      a.click();
      
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при изтеглянето на шаблона';
    }
  }
</script>

<svelte:head>
  <title>Импорт от PaperlessAI - VAT System</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-gray-900">Импорт от PaperlessAI</h1>
    <p class="mt-2 text-gray-600">
      Автоматично импортиране на обработени документи от PaperlessAI система
    </p>
  </div>

  <!-- Instructions -->
  <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
    <h3 class="text-lg font-medium text-blue-900 mb-4">Как работи импортирането:</h3>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="flex items-start">
        <div class="bg-blue-600 rounded-full p-2 text-white mr-3 mt-1">
          <span class="text-sm font-bold">1</span>
        </div>
        <div>
          <h4 class="font-medium text-blue-900">Експорт от PaperlessAI</h4>
          <p class="text-sm text-blue-700">Експортирайте обработените фактури като Excel или JSON файл</p>
        </div>
      </div>
      <div class="flex items-start">
        <div class="bg-blue-600 rounded-full p-2 text-white mr-3 mt-1">
          <span class="text-sm font-bold">2</span>
        </div>
        <div>
          <h4 class="font-medium text-blue-900">Качване и валидация</h4>
          <p class="text-sm text-blue-700">Качете файла тук за автоматична валидация и преглед</p>
        </div>
      </div>
      <div class="flex items-start">
        <div class="bg-blue-600 rounded-full p-2 text-white mr-3 mt-1">
          <span class="text-sm font-bold">3</span>
        </div>
        <div>
          <h4 class="font-medium text-blue-900">Одобрение и импорт</h4>
          <p class="text-sm text-blue-700">Прегледайте данните и одобрете за въвеждане в дневниците</p>
        </div>
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

  <!-- Upload Form -->
  {#if !processingResult}
    <div class="bg-white rounded-lg shadow-sm p-6 mb-8">
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-lg font-medium text-gray-900">Настройки за импорт</h3>
        
        <!-- Template download buttons -->
        <div class="flex space-x-2">
          <button
            on:click={() => downloadTemplate('purchase')}
            class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            📥 Шаблон покупки
          </button>
          <button
            on:click={() => downloadTemplate('sales')}
            class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            📥 Шаблон продажби
          </button>
        </div>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <!-- Company Selection -->
        <div>
          <label for="company-select-import" class="block text-sm font-medium text-gray-700 mb-2">Фирма</label>
          <select
            id="company-select-import"
            bind:value={selectedCompany}
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value={null}>Изберете фирма</option>
            {#each companies as company}
              <option value={company}>{company.name} ({company.uic})</option>
            {/each}
          </select>
        </div>

        <!-- Journal Type -->
        <div>
          <label for="journal-type-select" class="block text-sm font-medium text-gray-700 mb-2">Тип дневник</label>
          <select
            id="journal-type-select"
            bind:value={selectedJournalType}
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            {#each journalTypes as journalType}
              <option value={journalType.value}>{journalType.label}</option>
            {/each}
          </select>
          <p class="mt-1 text-sm text-gray-500">
            {journalTypes.find(jt => jt.value === selectedJournalType)?.description}
          </p>
        </div>
      </div>

      <!-- File Upload -->
      <div class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        {#if !uploadedFile}
          <Upload class="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h4 class="text-lg font-medium text-gray-900 mb-2">Качете PaperlessAI експорт</h4>
          <p class="text-gray-500 mb-4">Excel (.xlsx, .xls) или JSON файлове</p>
          
          <input
            type="file"
            accept=".xlsx,.xls,.json"
            on:change={handleFileSelect}
            class="hidden"
            id="file-upload"
          />
          
          <label
            for="file-upload"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 cursor-pointer"
          >
            <Upload class="h-4 w-4 mr-2" />
            Изберете файл
          </label>
          
          <button
            on:click={() => downloadTemplate(selectedJournalType)}
            class="ml-3 inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <Download class="h-4 w-4 mr-2" />
            Шаблон
          </button>
        {:else}
          <FileText class="h-12 w-12 text-green-500 mx-auto mb-4" />
          <h4 class="text-lg font-medium text-gray-900 mb-2">{uploadedFile.name}</h4>
          <p class="text-gray-500 mb-4">
            Размер: {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
          </p>
          
          <div class="flex justify-center space-x-3">
            <button
              on:click={processFile}
              disabled={!selectedCompany || isUploading}
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
            >
              {#if isUploading}
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Обработване...
              {:else}
                <CheckCircle class="h-4 w-4 mr-2" />
                Обработи файла
              {/if}
            </button>
            
            <button
              on:click={resetUpload}
              disabled={isUploading}
              class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Отказ
            </button>
          </div>
          
          {#if isUploading}
            <div class="mt-4">
              <div class="bg-gray-200 rounded-full h-2">
                <div class="bg-blue-600 h-2 rounded-full transition-all" style="width: {uploadProgress}%"></div>
              </div>
              <p class="text-sm text-gray-500 mt-2">Обработване: {uploadProgress}%</p>
            </div>
          {/if}
        {/if}
      </div>
    </div>
  {/if}

  <!-- Processing Results -->
  {#if processingResult}
    <div class="bg-white rounded-lg shadow-sm p-6 mb-8">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-lg font-medium text-gray-900">Резултати от обработката</h3>
        <button
          on:click={resetUpload}
          class="text-sm text-gray-500 hover:text-gray-700"
        >
          Нов импорт
        </button>
      </div>

      <!-- Summary -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-blue-50 rounded-lg p-4">
          <div class="flex items-center">
            <FileText class="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <p class="text-2xl font-bold text-blue-900">{processingResult.data?.total_records || 0}</p>
              <p class="text-sm text-blue-600">Общо записи</p>
            </div>
          </div>
        </div>
        
        <div class="bg-green-50 rounded-lg p-4">
          <div class="flex items-center">
            <CheckCircle class="h-8 w-8 text-green-600 mr-3" />
            <div>
              <p class="text-2xl font-bold text-green-900">
                {processingResult.validationResult?.valid_entries || processingResult.data?.total_records || 0}
              </p>
              <p class="text-sm text-green-600">Валидни записи</p>
            </div>
          </div>
        </div>
        
        <div class="bg-orange-50 rounded-lg p-4">
          <div class="flex items-center">
            <AlertCircle class="h-8 w-8 text-orange-600 mr-3" />
            <div>
              <p class="text-2xl font-bold text-orange-900">
                {processingResult.validationResult?.validation_errors || 0}
              </p>
              <p class="text-sm text-orange-600">Грешки</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Import Messages -->
      {#if processingResult.data?.import_messages && processingResult.data.import_messages.length > 0}
        <div class="mb-6">
          <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
              <h4 class="text-sm font-medium text-gray-900">Съобщения при обработката</h4>
              <div class="flex items-center space-x-2">
                {#if processingResult.data.has_errors}
                  <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    ❌ Грешки
                  </span>
                {/if}
                {#if processingResult.data.has_warnings}
                  <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    ⚠️ Предупреждения
                  </span>
                {/if}
              </div>
            </div>
            <div class="px-4 py-3 max-h-40 overflow-y-auto">
              {#each processingResult.data.import_messages as message}
                <div class="text-sm mb-1 {message.includes('❌') ? 'text-red-600' : message.includes('⚠️') ? 'text-yellow-600' : 'text-green-600'}">
                  {message}
                </div>
              {/each}
            </div>
          </div>
        </div>
      {/if}

      <!-- Preview Data -->
      {#if previewData && previewData.length > 0}
        <div class="mb-6">
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-md font-medium text-gray-900">Преглед на данните</h4>
            <button
              on:click={() => showPreview = !showPreview}
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              <Eye class="h-4 w-4 inline mr-1" />
              {showPreview ? 'Скрий' : 'Покажи'} подробности
            </button>
          </div>
          
          {#if showPreview}
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Документ</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Партньор</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Данъчна основа</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">ДДС</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Обща сума</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  {#each previewData.slice(0, 5) as entry}
                    <tr>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">{entry.data.document_number || 'Без номер'}</div>
                        <div class="text-sm text-gray-500">{entry.data.document_date || ''}</div>
                      </td>
                      <td class="px-6 py-4">
                        <div class="text-sm text-gray-900">
                          {entry.data.supplier_name || entry.data.customer_name || 'Неизвестен'}
                        </div>
                        <div class="text-sm text-gray-500">
                          {entry.data.supplier_vat || entry.data.customer_vat || ''}
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatCurrency(entry.data.tax_base || entry.data.tax_base_20 || 0)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatCurrency(entry.data.vat_amount || entry.data.vat_20 || 0)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                        {formatCurrency(entry.data.total_amount || 0)}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
              
              {#if previewData.length > 5}
                <p class="text-sm text-gray-500 text-center mt-4">
                  ... и още {previewData.length - 5} записа
                </p>
              {/if}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Action Buttons -->
      {#if !processingResult.imported}
        <div class="flex justify-end space-x-3">
          <button
            on:click={() => importEntries(false)}
            class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <Eye class="h-4 w-4 inline mr-2" />
            Само валидирай
          </button>
          
          <button
            on:click={() => importEntries(true)}
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
          >
            <CheckCircle class="h-4 w-4 mr-2" />
            Импортирай в дневниците
          </button>
        </div>
      {:else}
        <div class="text-center py-6">
          <CheckCircle class="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-green-900 mb-2">Импортирането завърши успешно!</h3>
          <p class="text-green-700">
            Импортирани {processingResult.importResult?.data?.imported_count || 0} записа в {
              selectedJournalType === 'purchase' ? 'дневника на покупките' : 'дневника за продажбите'
            }
          </p>
          
          <div class="mt-6 flex justify-center space-x-3">
            <a
              href="/journals/{selectedJournalType}s"
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Виж дневника
            </a>
            
            <button
              on:click={resetUpload}
              class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Нов импорт
            </button>
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Supported Formats Info -->
  <div class="bg-gray-50 rounded-lg p-6">
    <h3 class="text-lg font-medium text-gray-900 mb-4">Поддържани формати</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <h4 class="font-medium text-gray-900 mb-2">Excel файлове (.xlsx, .xls)</h4>
        <ul class="text-sm text-gray-600 space-y-1">
          <li>• Стандартният експорт от PaperlessAI</li>
          <li>• Поддържа множество листове (Summary, Supplier Details, и др.)</li>
          <li>• Автоматично разпознаване на колони</li>
        </ul>
      </div>
      <div>
        <h4 class="font-medium text-gray-900 mb-2">JSON файлове</h4>
        <ul class="text-sm text-gray-600 space-y-1">
          <li>• Структурирани JSON експорти</li>
          <li>• Запазва всички метаданни</li>
          <li>• По-точно мапиране на полетата</li>
        </ul>
      </div>
    </div>
  </div>
</div>