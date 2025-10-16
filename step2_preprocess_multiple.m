function step2_preprocess_multiple(input_folders, output_folder)
    if nargin < 2
        error('Please provide input_folders (cell array) and output_folder');
    end

    if ~exist(output_folder, 'dir'), mkdir(output_folder); end
    output_interp_mat_folder = fullfile(output_folder, 'interp_chan');
    if ~exist(output_interp_mat_folder, 'dir'), mkdir(output_interp_mat_folder); end

    % === Create log file ===
    log_file = fullfile(output_folder, 'step2_log.txt');
    fid = fopen(log_file, 'a');  % 'a' for append, 'w' for overwrite
    if fid == -1
        error('Failed to create log file');
    end
    cleanupObj = onCleanup(@() fclose(fid));

    % Iterate through each folder
    for folder_idx = 1:length(input_folders)
        input_folder = input_folders{folder_idx};
        file_list = dir(fullfile(input_folder, '*.vhdr'));

        for i = 1:length(file_list)
            try
                filename = file_list(i).name;
                [~, file_name_noext, ~] = fileparts(filename);
                subj_id = strtok(file_name_noext, '_');

                % Log processing start
                msg = sprintf(' Processing: %s\n', filename);
                fprintf('%s', msg); fprintf(fid, '%s', msg);

                % === EEGLAB pipeline ===
                [ALLEEG, EEG, CURRENTSET, ALLCOM] = eeglab('nogui');  % Suppress GUI output
                EEG = pop_loadbv(input_folder, filename);

                % Basic preprocessing
                fprintf(fid, 'Filtering...');
                EEG = pop_chanedit(EEG, 'lookup', 'standard_1005.elc');
                EEG = pop_eegfiltnew(EEG, 'hicutoff', 45);
                EEG = pop_eegfiltnew(EEG, 'locutoff', 0.1);
                EEG = pop_eegfiltnew(EEG, 'locutoff', 49, 'hicutoff', 51, 'revfilt', 1);
                
                fprintf(fid, 'Cleaning rawdata...');
                EEG = pop_clean_rawdata(EEG, 'FlatlineCriterion', 5, ...
                    'ChannelCriterion', 0.8, 'LineNoiseCriterion', 4, ...
                    'Highpass', 'off', 'BurstCriterion', 20, ...
                    'WindowCriterion', 0.25, 'BurstRejection', 'on');

                EEG = pop_resample(EEG, 500);

                % Reject bad channels
                fprintf(fid, 'Rejecting bad channels...');
                [EEG, ~] = pop_rejchan(EEG, 'elec', 1:EEG.nbchan, 'threshold', [-3 3], ...
                    'norm', 'on', 'measure', 'spec', 'freqrange', [0.5 45]);
                [EEG, ~] = pop_rejchan(EEG, 'elec', 1:EEG.nbchan, 'threshold', [-3 3], ...
                    'norm', 'on', 'measure', 'spec', 'freqrange', [0.5 45]);

                % Record interpolated channels
                if isfield(EEG.chaninfo, 'removedchans') && ~isempty(EEG.chaninfo.removedchans)
                    removed_info = EEG.chaninfo.removedchans;
                    removed_labels = {removed_info.labels};
                    removed_urchan = [removed_info.urchan];
                    T = table(removed_urchan(:), removed_labels(:), ...
                              'VariableNames', {'urchan', 'label'});
                    EEG.etc.interp_chan = T;
                else
                    EEG.etc.interp_chan = table();
                end

                % Interpolation
                EEG = pop_interp(EEG, EEG.chaninfo.removedchans, 'spherical');

                % ICA
                fprintf(fid, 'Doing ICA...');
                EEG = pop_runica(EEG, 'icatype', 'runica', 'extended', 1, 'interrupt', 'on');
                EEG = pop_iclabel(EEG, 'default');
                EEG = pop_icflag(EEG, [NaN NaN; 0.9 1; 0.9 1; 0.9 1; 0.9 1; 0.9 1; NaN NaN]);
                EEG = pop_subcomp(EEG, [], 0);

                % Re-reference
                EEG = pop_reref(EEG, []);

                % Save preprocessed data
                fprintf(fid, 'Saving data...');
                EEG = pop_saveset(EEG, 'filename', sprintf('%s_processed.set', file_name_noext), ...
                    'filepath', output_folder);

                % Save interpolated channels
                interp_chan_struct = table2struct(EEG.etc.interp_chan);
                save(fullfile(output_interp_mat_folder, [subj_id '_interp_chan.mat']), ...
                    'interp_chan_struct');
                msg2 = sprintf('\n Saved interp_chan: %s_interp_chan.mat', subj_id);
                fprintf(fid, '%s', msg2);

                msg3 = sprintf('\n Folder %d/%d | File %d/%d processed successfully.', ...
                    folder_idx, length(input_folders), i, length(file_list));
                fprintf(fid, '%s', msg3);
            catch ME
                % Log errors
                err_msg = sprintf('\n Failed to process: %s\nError message: %s', filename, ME.message);
                fprintf(fid, '%s', err_msg);
            end
     
        end
    end

    fprintf(fid, '\n All files processed.\n');
  
end
