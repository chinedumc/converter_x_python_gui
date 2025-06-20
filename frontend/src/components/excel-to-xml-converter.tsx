"use client";

import React, { useState, useCallback, useEffect, useId } from "react";

// Escapes special XML characters in a string
function escapeXml(unsafe: string): string {
	return unsafe
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&apos;");
}
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { convertFile } from "@/lib/api";
import {
	PlusCircle,
	Trash2,
	UploadCloud,
	FileCog,
	AlertCircle,
	CheckCircle,
	Info,
	Eye,
} from "lucide-react";

interface HeaderField {
	id: string;
	tagName: string;
	tagValue: string;
}

export function ExcelToXmlConverter() {
	const [headerFields, setHeaderFields] = useState<HeaderField[]>([]);
	const [currentTagName, setCurrentTagName] = useState<string>("");
	const [currentTagValue, setCurrentTagValue] = useState<string>("");
	const [currentTagNameError, setCurrentTagNameError] = useState<
		string | undefined
	>(undefined);
	const [currentTagValueError, setCurrentTagValueError] = useState<
		string | undefined
	>(undefined);

	const [excelFile, setExcelFile] = useState<File | null>(null);
	const [originalFileName, setOriginalFileName] = useState<string>("");
	const [conversionProgress, setConversionProgress] = useState<number>(0);
	const [conversionStatus, setConversionStatus] = useState<
		"idle" | "validating" | "converting" | "completed" | "error"
	>("idle");

	const [statusMessage, setStatusMessage] = useState<string | null>(null);
	const { toast } = useToast();
	const formId = useId();

	const resetConverter = useCallback(() => {
		setHeaderFields([]);
		setCurrentTagName("");
		setCurrentTagValue("");
		setCurrentTagNameError(undefined);
		setCurrentTagValueError(undefined);
		setExcelFile(null);
		setOriginalFileName("");
		setConversionProgress(0);
		setConversionStatus("idle");
		setStatusMessage(null);

		// Reset file input
		const fileInput = document.getElementById(
			`${formId}-file-upload`
		) as HTMLInputElement;
		if (fileInput) {
			fileInput.value = "";
		}
	}, [formId]);

	const validateTagName = (name: string): string | undefined => {
		if (!name.trim()) return "Tag name cannot be empty.";
		if (!/^[a-zA-Z_][\w.-]*$/.test(name))
			return "Invalid XML tag name format. Use letters, numbers, underscore, period, or hyphen. Must start with a letter or underscore.";
		return undefined;
	};

	const validateTagValue = (value: string): string | undefined => {
		// Allowing empty tag values
		return undefined;
	};

	const handleCurrentTagNameChange = (value: string) => {
		setCurrentTagName(value);
		if (value.trim()) {
			// Only validate if not empty, error for empty is handled on add
			setCurrentTagNameError(validateTagName(value));
		} else {
			setCurrentTagNameError(undefined); // Clear error if user clears input
		}
	};

	const handleCurrentTagValueChange = (value: string) => {
		setCurrentTagValue(value);
		setCurrentTagValueError(validateTagValue(value)); // Validate immediately, empty is allowed
	};

	const handleAddNewHeaderField = () => {
		const tagNameError = validateTagName(currentTagName);
		const tagValueError = validateTagValue(currentTagValue);

		if (tagNameError) {
			setCurrentTagNameError(tagNameError);
			toast({
				title: "Validation Error",
				description: tagNameError,
				variant: "destructive",
			});
			return;
		}

		// Check for duplicate tag names
		const isDuplicate = headerFields.some(
			(field) => field.tagName === currentTagName.trim()
		);
		if (isDuplicate) {
			const error = "Tag name already exists. Please use a unique name.";
			setCurrentTagNameError(error);
			toast({
				title: "Validation Error",
				description: error,
				variant: "destructive",
			});
			return;
		}

		setCurrentTagNameError(undefined);
		setCurrentTagValueError(undefined);

		setHeaderFields([
			...headerFields,
			{
				id: Date.now().toString(),
				tagName: currentTagName.trim(),
				tagValue: currentTagValue.trim(),
			},
		]);

		// Reset input fields
		setCurrentTagName("");
		setCurrentTagValue("");

		toast({
			title: "Success",
			description: "Header field added successfully.",
		});
	};

	const handleRemoveHeaderField = (idToRemove: string) => {
		const updatedFields = headerFields.filter(
			(field) => field.id !== idToRemove
		);
		setHeaderFields(updatedFields);
	};

	const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (!file) {
			setExcelFile(null);
			setOriginalFileName("");
			return;
		}

		const validTypes = [
			"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			"application/vnd.ms-excel",
			".xlsx",
			".xls",
		];

		const isValidType = validTypes.some(
			(type) => file.type === type || file.name.toLowerCase().endsWith(type)
		);

		if (isValidType) {
			setExcelFile(file);
			setOriginalFileName(file.name);
			setStatusMessage(null);
			setConversionStatus("idle");
		} else {
			setExcelFile(null);
			setOriginalFileName("");
			setStatusMessage("Invalid file type. Please upload a valid Excel file.");
			setConversionStatus("error");
			event.target.value = "";
			toast({
				title: "Invalid File Type",
				description: "Please upload a valid Excel file (.xlsx, .xls).",
				variant: "destructive",
			});
		}
	};

	const validateAllInputsBeforeConversion = (): boolean => {
		if (!excelFile) {
			toast({
				title: "Missing File",
				description: "Please upload an Excel file.",
				variant: "destructive",
			});
			return false;
		}

		// Validate that at least one header field is added
		if (headerFields.length === 0) {
			toast({
				title: "Validation Error",
				description: "Please add at least one header field before conversion.",
				variant: "destructive",
			});
			return false;
		}

		// Validate any incomplete header fields
		if (currentTagName || currentTagValue) {
			toast({
				title: "Incomplete Header Field",
				description:
					"Please add or clear the current header field before converting.",
				variant: "destructive",
			});
			return false;
		}

		// Validate header field names are unique
		const tagNames = headerFields.map((field) => field.tagName);
		const duplicates = tagNames.filter(
			(name, index) => tagNames.indexOf(name) !== index
		);
		if (duplicates.length > 0) {
			toast({
				title: "Duplicate Header Fields",
				description: `Found duplicate tag names: ${duplicates.join(
					", "
				)}. Please ensure all tag names are unique.`,
				variant: "destructive",
			});
			return false;
		}

		return true;
	};

	const handleConvert = async () => {
		setConversionStatus("validating");
		setStatusMessage(null);

		if (!validateAllInputsBeforeConversion()) {
			setConversionStatus("error");
			setStatusMessage("Please fix the errors in the form.");
			return;
		}

		setConversionStatus("converting");
		setStatusMessage("Conversion in progress...");
		setConversionProgress(0);

		const progressInterval = setInterval(() => {
			setConversionProgress((prev) => {
				if (prev >= 100) {
					clearInterval(progressInterval);
					return 100;
				}
				return prev + 10;
			});
		}, 200);

		try {
			// Prepare request data with header fields
			const requestData = {
				header_fields: headerFields.map((field) => ({
					tagName: field.tagName,
					tagValue: field.tagValue,
				})),
			};

			const file = excelFile!;
			const formData = new FormData();
			formData.append("file", file);
			formData.append("header_fields", JSON.stringify(headerFields));

			const response = await fetch("/api/v1/convert", {
				method: "POST",
				body: formData, // <-- This is important!
			});

			if (!response.ok) {
				throw new Error("Failed to convert file. Please try again.");
			}

			const result = await response.json();

			clearInterval(progressInterval);
			setConversionProgress(100);
			setConversionStatus("completed");
			setStatusMessage(
				"Conversion successful! Your XML file is ready for download."
			);

			// Trigger download using the full API base URL
			window.location.href = result.downloadUrl;
		} catch (error) {
			clearInterval(progressInterval);
			setConversionStatus("error");
			setStatusMessage(
				error instanceof Error
					? error.message
					: "An unknown error occurred during conversion."
			);
			toast({
				title: "Conversion Error",
				description:
					error instanceof Error ? error.message : "An unknown error occurred.",
				variant: "destructive",
			});
		}
	};

	const getStatusAlertVariant = (): "default" | "destructive" | undefined => {
		if (conversionStatus === "error") return "destructive";
		if (conversionStatus === "completed") return "default";
		return "default";
	};

	const getStatusAlertIcon = () => {
		if (conversionStatus === "completed")
			return <CheckCircle className="h-4 w-4" />;
		if (conversionStatus === "error")
			return <AlertCircle className="h-4 w-4" />;
		if (conversionStatus === "converting" || conversionStatus === "validating")
			return <Info className="h-4 w-4" />;
		return null;
	};

	return (
		<Card className="w-full max-w-2xl mx-auto shadow-2xl">
			<CardHeader>
				<CardTitle className="text-3xl font-headline text-center text-primary">
					Excel2XML Converter
				</CardTitle>
				<CardDescription className="text-center">
					Define XML headers, upload an Excel file, and convert it to XML
					format.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				<div className="space-y-4 p-4 border rounded-md shadow-sm">
					<h3 className="text-lg font-semibold text-accent mb-4">
						1. Define XML Header
					</h3>

					<div className="space-y-3 p-3 border-b border-border pb-6">
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
							<div>
								<Label htmlFor={`${formId}-current-tag-name`}>
									New Tag Name
								</Label>
								<Input
									id={`${formId}-current-tag-name`}
									placeholder="e.g., CALLREPORT_ID"
									value={currentTagName}
									onChange={(e) => handleCurrentTagNameChange(e.target.value)}
									className={
										currentTagNameError
											? "border-destructive ring-destructive"
											: ""
									}
									aria-invalid={!!currentTagNameError}
									aria-describedby={
										currentTagNameError
											? `${formId}-current-tag-name-error`
											: undefined
									}
								/>
								{currentTagNameError && (
									<p
										id={`${formId}-current-tag-name-error`}
										className="text-xs text-destructive mt-1"
									>
										{currentTagNameError}
									</p>
								)}
							</div>
							<div>
								<Label htmlFor={`${formId}-current-tag-value`}>
									New Tag Value
								</Label>
								<Input
									id={`${formId}-current-tag-value`}
									placeholder="e.g., DTR001"
									value={currentTagValue}
									onChange={(e) => handleCurrentTagValueChange(e.target.value)}
									className={
										currentTagValueError
											? "border-destructive ring-destructive"
											: ""
									} // This error state might not be used if values can be empty
									aria-invalid={!!currentTagValueError}
									aria-describedby={
										currentTagValueError
											? `${formId}-current-tag-value-error`
											: undefined
									}
								/>
								{/* currentTagValueError display can be omitted if empty values are always fine and no other validation rules */}
							</div>
						</div>
						<Button
							onClick={handleAddNewHeaderField}
							className="mt-3 border-primary text-primary hover:bg-primary/10 hover:text-primary w-full md:w-auto"
						>
							<PlusCircle className="mr-2 h-4 w-4" /> Add This Header Field
						</Button>
					</div>

					<div className="mt-4 p-4 border rounded-md bg-muted/20 shadow-inner">
						<div className="flex items-center mb-3">
							<Eye className="h-5 w-5 mr-2 text-accent" />
							<h4 className="text-md font-semibold text-accent">
								Configured Header Tags
							</h4>
						</div>
						{headerFields.length > 0 ? (
							<ul className="space-y-2">
								{headerFields.map((field) => (
									<li
										key={field.id}
										className="flex justify-between items-center p-2.5 bg-background rounded-md border border-input shadow-sm hover:shadow-md transition-shadow duration-150 ease-in-out"
									>
										<code className="text-sm text-foreground break-all mr-3 flex-grow select-all">
											{`<${escapeXml(field.tagName)}>${escapeXml(
												field.tagValue
											)}</${escapeXml(field.tagName)}>`}
										</code>
										<Button
											onClick={() => handleRemoveHeaderField(field.id)}
											className="text-destructive hover:bg-destructive/10 shrink-0"
											aria-label={`Remove header field ${field.tagName}`}
										>
											<Trash2 className="h-4 w-4" />
										</Button>
									</li>
								))}
							</ul>
						) : (
							<p className="text-sm text-muted-foreground italic text-center py-2">
								No header fields defined. Use the inputs above to add tags.
							</p>
						)}
					</div>
				</div>

				<Separator />

				<div className="space-y-2 p-4 border rounded-md shadow-sm">
					<h3 className="text-lg font-semibold text-accent">
						2. Upload Excel File
					</h3>
					<Label htmlFor={`${formId}-file-upload`}>
						Select .xlsx or .xls file
					</Label>
					<Input
						id={`${formId}-file-upload`}
						type="file"
						accept=".xlsx, .xls, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
						onChange={handleFileChange}
						className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
						aria-describedby={`${formId}-file-name`}
					/>
					<p
						id={`${formId}-file-name`}
						className="text-sm text-muted-foreground"
					>
						{originalFileName
							? `Selected file: ${originalFileName}`
							: "No file selected."}
					</p>
				</div>

				<Separator />

				<div className="space-y-4 p-4 border rounded-md shadow-sm">
					<h3 className="text-lg font-semibold text-accent">
						3. Convert & Download
					</h3>
					<Button
						onClick={handleConvert}
						disabled={
							conversionStatus === "converting" ||
							conversionStatus === "validating"
						}
						className="w-full bg-primary hover:bg-primary/90 text-primary-foreground text-lg py-6"
					>
						<FileCog className="mr-2 h-5 w-5" />
						{conversionStatus === "converting"
							? "Converting..."
							: "Convert to XML"}
					</Button>

					{(conversionStatus === "converting" ||
						conversionStatus === "completed" ||
						conversionStatus === "error" ||
						conversionStatus === "validating") && (
						<div className="space-y-2 mt-4">
							<Progress
								value={conversionProgress}
								className="w-full transition-all duration-300 ease-linear"
							/>
							{statusMessage && (
								<Alert
									variant={getStatusAlertVariant()}
									className="mt-2 transition-opacity duration-300"
								>
									{getStatusAlertIcon()}
									<AlertTitle>
										{conversionStatus === "completed"
											? "Success!"
											: conversionStatus === "error"
											? "Error!"
											: conversionStatus === "converting"
											? "Processing..."
											: conversionStatus === "validating"
											? "Validating..."
											: "Status"}
									</AlertTitle>
									<AlertDescription>{statusMessage}</AlertDescription>
								</Alert>
							)}
						</div>
					)}
				</div>

				{conversionStatus === "completed" && (
					<Button
						onClick={resetConverter}
						className="w-full mt-4 text-lg py-6 border-primary text-primary hover:bg-primary/10"
					>
						Convert Another File
					</Button>
				)}
				{conversionStatus === "error" && (
					<Button
						onClick={resetConverter}
						className="w-full mt-4 text-lg py-6 border-primary text-primary hover:bg-primary/10"
					>
						Try Again
					</Button>
				)}
			</CardContent>
			<CardFooter className="flex justify-center">
				<p className="text-xs text-muted-foreground">
					Excel2XML Converter &copy; {new Date().getFullYear()}
				</p>
			</CardFooter>
		</Card>
	);
}
